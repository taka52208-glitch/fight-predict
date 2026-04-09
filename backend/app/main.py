import os
import logging
import asyncio
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.models.fighter import Fighter, Prediction, PredictionRecord, AccuracyStats
from app.services.ufc_scraper import (
    search_fighter,
    suggest_fighters,
    get_upcoming_events,
    get_event_fights,
)
from app.services.rizin_scraper import (
    search_rizin_fighter,
    suggest_rizin_fighters,
    get_upcoming_rizin_events,
    get_rizin_event_fights,
)
from app.services.rizin_cache import suggest_rizin_all, get_all_jp_names
from app.services.predictor import calculate_prediction
from app.services.prediction_tracker import (
    save_prediction,
    record_result,
    get_accuracy_stats,
    get_pending_predictions,
)
from app.services.report_generator import generate_note_article, generate_x_posts
from app.services.name_mapping import get_romaji_query

logger = logging.getLogger(__name__)

app = FastAPI(title="格闘技試合予測ツール", version="1.0.0")

# カンマ区切りで許可するオリジンを指定 (例: "https://fight-predict.vercel.app,http://localhost:5173")
# 未設定時は "*" (開発用 — 本番では環境変数 ALLOWED_ORIGINS を設定すること)
_allowed = os.getenv("ALLOWED_ORIGINS", "*")
allow_origins = [o.strip() for o in _allowed.split(",")] if _allowed != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_preload():
    """Pre-load UFC fighter cache and RIZIN cache at startup (non-blocking)."""
    from app.services.ufc_scraper import load_fighter_cache
    from app.services.rizin_cache import preload_rizin_cache

    from app.services.ml_model import train_model_from_history

    asyncio.create_task(load_fighter_cache())
    asyncio.create_task(preload_rizin_cache())
    asyncio.create_task(train_model_from_history())
    logger.info("Startup cache loading + ML training tasks dispatched")


def _is_japanese(text: str) -> bool:
    """Check if text contains Japanese characters."""
    for ch in text:
        if '\u3000' <= ch <= '\u9fff' or '\uff00' <= ch <= '\uffef':
            return True
    return False


def _resolve_name(name: str) -> str:
    """Translate Japanese name to English if needed."""
    if _is_japanese(name):
        name = name.strip()
        # Check RIZIN cache mapping
        jp_map = get_all_jp_names()
        # Exact match first
        if name in jp_map:
            return jp_map[name]
        # Partial match - prefer longer keys (more specific) and require minimum overlap
        best_match = None
        best_len = 0
        for jp, en in jp_map.items():
            if name in jp or jp in name:
                if len(jp) > best_len:
                    best_match = en
                    best_len = len(jp)
        if best_match:
            return best_match
        # Romaji fallback
        romaji = get_romaji_query(name)
        if romaji:
            return romaji
    return name


# Allowed domains for event URL fetching (SSRF protection)
_ALLOWED_EVENT_DOMAINS = {"ufcstats.com", "www.ufcstats.com", "www.sherdog.com", "sherdog.com"}


def _validate_event_url(url: str) -> bool:
    """Validate that an event URL belongs to an allowed domain."""
    try:
        parsed = urlparse(url)
        return parsed.hostname in _ALLOWED_EVENT_DOMAINS
    except Exception:
        return False


@app.get("/")
async def root():
    return {"message": "格闘技試合予測ツール API"}


async def _find_fighter(name: str, org: str):
    """Try primary org, fall back to the other org if not found."""
    resolved = _resolve_name(name)
    try:
        if org.lower() == "ufc":
            fighter = await search_fighter(resolved)
            if not fighter:
                fighter = await search_rizin_fighter(resolved)
        else:
            fighter = await search_rizin_fighter(resolved)
            if not fighter:
                fighter = await search_fighter(resolved)
        return fighter
    except Exception as e:
        logger.error(f"Error finding fighter '{name}' (resolved: '{resolved}'): {e}")
        return None


@app.get("/api/fighter/{name}")
async def get_fighter(name: str, org: str = "ufc") -> Fighter:
    """Search for a fighter by name (supports Japanese, falls back to other org)."""
    if len(name) > 100:
        raise HTTPException(status_code=400, detail="選手名が長すぎます")

    fighter = await _find_fighter(name, org)

    if not fighter:
        raise HTTPException(status_code=404, detail=f"選手 '{name}' が見つかりません")

    return fighter


@app.get("/api/suggest")
async def suggest(q: str = Query(..., max_length=100), org: str = "ufc"):
    """Suggest fighters matching a partial name query (supports Japanese)."""
    if not q:
        return []

    # RIZIN mode: use comprehensive RIZIN cache (supports Japanese)
    if org.lower() == "rizin":
        results = await suggest_rizin_all(q)
        if results:
            return results
        # Romaji fallback for Japanese input not in cache
        if _is_japanese(q):
            romaji = get_romaji_query(q)
            if romaji:
                results = await suggest_rizin_fighters(romaji)
                if results:
                    return results
        if len(q) >= 2:
            return await suggest_rizin_fighters(q)
        return []

    # UFC mode
    if _is_japanese(q):
        # Check RIZIN cache for Japanese names (some UFC fighters have JP names)
        results = await suggest_rizin_all(q)
        if results:
            return results
        romaji = get_romaji_query(q)
        if romaji and len(romaji) >= 2:
            return await suggest_fighters(romaji)
        return []

    if len(q) < 2:
        return []

    return await suggest_fighters(q)


@app.get("/api/events/upcoming")
async def upcoming_events(org: str = "all"):
    """Get upcoming events."""
    events = []

    if org in ("all", "ufc"):
        ufc_events = await get_upcoming_events()
        for e in ufc_events:
            e["organization"] = "UFC"
        events.extend(ufc_events)

    if org in ("all", "rizin"):
        rizin_events = await get_upcoming_rizin_events()
        for e in rizin_events:
            e["organization"] = "RIZIN"
        events.extend(rizin_events)

    return events


@app.get("/api/events/{org}/{event_url:path}/fights")
async def event_fights(org: str, event_url: str):
    """Get fight card for a specific event."""
    if not _validate_event_url(event_url):
        raise HTTPException(status_code=400, detail="無効なイベントURLです")

    if org.lower() == "ufc":
        fights = await get_event_fights(event_url)
    else:
        fights = await get_rizin_event_fights(event_url)

    return fights


@app.get("/api/predict")
async def predict_fight(fighter_a: str, fighter_b: str, org: str = "ufc") -> Prediction:
    """Predict the outcome of a fight between two fighters (supports Japanese)."""
    if len(fighter_a) > 100 or len(fighter_b) > 100:
        raise HTTPException(status_code=400, detail="選手名が長すぎます")

    fa = await _find_fighter(fighter_a, org)
    fb = await _find_fighter(fighter_b, org)

    if not fa:
        raise HTTPException(status_code=404, detail=f"選手 '{fighter_a}' が見つかりません")
    if not fb:
        raise HTTPException(status_code=404, detail=f"選手 '{fighter_b}' が見つかりません")

    from app.models.fighter import Fight
    fight = Fight(
        fighter_a=fa.name,
        fighter_b=fb.name,
        weight_class=fa.weight_class or fb.weight_class,
        organization=org.upper(),
    )

    prediction = calculate_prediction(fa, fb, fight)

    # Auto-save prediction for accuracy tracking
    try:
        save_prediction(prediction, org)
    except Exception as e:
        logger.warning(f"Failed to save prediction record: {e}")

    return prediction


@app.get("/api/predict/event")
async def predict_event(event_url: str, org: str = "ufc") -> list[Prediction]:
    """Predict all fights in an upcoming event."""
    if not _validate_event_url(event_url):
        raise HTTPException(status_code=400, detail="無効なイベントURLです")

    if org.lower() == "ufc":
        fights = await get_event_fights(event_url)
    else:
        fights = await get_rizin_event_fights(event_url)

    predictions = []
    for fight in fights:
        try:
            if org.lower() == "ufc":
                fa = await search_fighter(fight.fighter_a)
                fb = await search_fighter(fight.fighter_b)
            else:
                fa = await search_rizin_fighter(fight.fighter_a)
                fb = await search_rizin_fighter(fight.fighter_b)

            if fa and fb:
                pred = calculate_prediction(fa, fb, fight)
                predictions.append(pred)
        except (ValueError, AttributeError, KeyError) as e:
            logger.warning(f"Failed to predict fight {fight.fighter_a} vs {fight.fighter_b}: {e}")
            continue

    return predictions


# ===== Prediction Tracking =====

@app.post("/api/predictions/save")
async def save_prediction_record(
    fighter_a: str, fighter_b: str, org: str = "ufc"
) -> PredictionRecord:
    """Save a prediction to history for accuracy tracking."""
    if len(fighter_a) > 100 or len(fighter_b) > 100:
        raise HTTPException(status_code=400, detail="選手名が長すぎます")

    fa = await _find_fighter(fighter_a, org)
    fb = await _find_fighter(fighter_b, org)
    if not fa:
        raise HTTPException(status_code=404, detail=f"選手 '{fighter_a}' が見つかりません")
    if not fb:
        raise HTTPException(status_code=404, detail=f"選手 '{fighter_b}' が見つかりません")

    from app.models.fighter import Fight
    fight = Fight(
        fighter_a=fa.name, fighter_b=fb.name,
        weight_class=fa.weight_class or fb.weight_class,
        organization=org.upper(),
    )
    prediction = calculate_prediction(fa, fb, fight)
    record = save_prediction(prediction, org)
    return record


@app.post("/api/predictions/{prediction_id}/result")
async def set_prediction_result(prediction_id: str, winner: str) -> PredictionRecord:
    """Record the actual winner of a fight."""
    result = record_result(prediction_id, winner)
    if not result:
        raise HTTPException(status_code=404, detail="予測が見つかりません")
    return result


@app.get("/api/predictions/accuracy")
async def prediction_accuracy() -> AccuracyStats:
    """Get prediction accuracy statistics."""
    return get_accuracy_stats()


@app.get("/api/predictions/pending")
async def pending_predictions() -> list[PredictionRecord]:
    """Get predictions that haven't been resolved yet."""
    return get_pending_predictions()


# ===== Content Generation (note / X) =====

@app.get("/api/generate/note")
async def generate_note(event_url: str, org: str = "ufc"):
    """Generate a note article from event predictions."""
    if not _validate_event_url(event_url):
        raise HTTPException(status_code=400, detail="無効なイベントURLです")

    if org.lower() == "ufc":
        fights = await get_event_fights(event_url)
    else:
        fights = await get_rizin_event_fights(event_url)

    if not fights:
        raise HTTPException(status_code=404, detail="対戦カードが見つかりません")

    event_name = fights[0].event_name if fights[0].event_name else "大会"
    predictions = []
    fighter_pairs = []

    for fight in fights:
        try:
            if org.lower() == "ufc":
                fa = await search_fighter(fight.fighter_a)
                fb = await search_fighter(fight.fighter_b)
            else:
                fa = await search_rizin_fighter(fight.fighter_a)
                fb = await search_rizin_fighter(fight.fighter_b)

            if fa and fb:
                pred = calculate_prediction(fa, fb, fight)
                predictions.append(pred)
                fighter_pairs.append((fa, fb))
        except Exception as e:
            logger.warning(f"Skipping fight for report: {e}")
            continue

    if not predictions:
        raise HTTPException(status_code=404, detail="予測を生成できませんでした")

    # Get accuracy stats if available
    accuracy_pct = None
    try:
        stats = get_accuracy_stats()
        if stats.total >= 5:
            accuracy_pct = stats.accuracy
    except Exception:
        pass

    article = generate_note_article(event_name, predictions, fighter_pairs, accuracy_pct)
    return article


@app.get("/api/generate/x-posts")
async def generate_x(event_url: str, org: str = "ufc"):
    """Generate X (Twitter) posts from event predictions."""
    if not _validate_event_url(event_url):
        raise HTTPException(status_code=400, detail="無効なイベントURLです")

    if org.lower() == "ufc":
        fights = await get_event_fights(event_url)
    else:
        fights = await get_rizin_event_fights(event_url)

    if not fights:
        raise HTTPException(status_code=404, detail="対戦カードが見つかりません")

    event_name = fights[0].event_name if fights[0].event_name else "大会"
    predictions = []

    for fight in fights:
        try:
            if org.lower() == "ufc":
                fa = await search_fighter(fight.fighter_a)
                fb = await search_fighter(fight.fighter_b)
            else:
                fa = await search_rizin_fighter(fight.fighter_a)
                fb = await search_rizin_fighter(fight.fighter_b)

            if fa and fb:
                pred = calculate_prediction(fa, fb, fight)
                predictions.append(pred)
        except Exception as e:
            logger.warning(f"Skipping fight for X post: {e}")
            continue

    if not predictions:
        raise HTTPException(status_code=404, detail="予測を生成できませんでした")

    posts = generate_x_posts(event_name, predictions)
    return posts
