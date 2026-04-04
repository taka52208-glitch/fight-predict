import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models.fighter import Fighter, Prediction
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
from app.services.name_mapping import get_romaji_query

app = FastAPI(title="格闘技試合予測ツール", version="1.0.0")

# カンマ区切りで許可するオリジンを指定 (例: "https://fight-predict.vercel.app,http://localhost:5173")
# 未設定時は "*" (開発用)
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
    """Pre-load UFC fighter cache and RIZIN cache at startup."""
    import asyncio
    from app.services.ufc_scraper import load_fighter_cache
    from app.services.rizin_cache import preload_rizin_cache

    asyncio.create_task(load_fighter_cache())
    asyncio.create_task(preload_rizin_cache())


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
        # Exact match
        if name in jp_map:
            return jp_map[name]
        # Partial match
        for jp, en in jp_map.items():
            if name in jp or jp in name:
                return en
        # Romaji fallback
        romaji = get_romaji_query(name)
        if romaji:
            return romaji
    return name


@app.get("/")
async def root():
    return {"message": "格闘技試合予測ツール API"}


async def _find_fighter(name: str, org: str):
    """Try primary org, fall back to the other org if not found."""
    resolved = _resolve_name(name)
    if org.lower() == "ufc":
        fighter = await search_fighter(resolved)
        if not fighter:
            fighter = await search_rizin_fighter(resolved)
    else:
        fighter = await search_rizin_fighter(resolved)
        if not fighter:
            fighter = await search_fighter(resolved)
    return fighter


@app.get("/api/fighter/{name}")
async def get_fighter(name: str, org: str = "ufc") -> Fighter:
    """Search for a fighter by name (supports Japanese, falls back to other org)."""
    fighter = await _find_fighter(name, org)

    if not fighter:
        raise HTTPException(status_code=404, detail=f"選手 '{name}' が見つかりません")

    return fighter


@app.get("/api/suggest")
async def suggest(q: str, org: str = "ufc"):
    """Suggest fighters matching a partial name query (supports Japanese)."""
    if not q or len(q) < 1:
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
    if org.lower() == "ufc":
        fights = await get_event_fights(event_url)
    else:
        fights = await get_rizin_event_fights(event_url)

    return fights


@app.get("/api/predict")
async def predict_fight(fighter_a: str, fighter_b: str, org: str = "ufc") -> Prediction:
    """Predict the outcome of a fight between two fighters (supports Japanese)."""
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
    return prediction


@app.get("/api/predict/event")
async def predict_event(event_url: str, org: str = "ufc") -> list[Prediction]:
    """Predict all fights in an upcoming event."""
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
        except Exception:
            continue

    return predictions
