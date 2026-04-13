"""Machine learning model for fight prediction.

Uses logistic regression trained on historical UFC fight data.
Extracts 12 feature differences from fighter stats and predicts
the probability of fighter A winning.

The ML prediction is blended with the existing rule-based scoring
to produce the final prediction.
"""

import logging
import os
import asyncio

import numpy as np
import joblib
from sklearn.linear_model import LogisticRegression

logger = logging.getLogger(__name__)

# Model is stored in the repo so it survives Render redeploys
_MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "model")
_MODEL_FILE = os.path.join(_MODEL_DIR, "fight_model.joblib")

_model: LogisticRegression | None = None
_model_ready = False
_training_status = "idle"  # idle / loading / training / ready / failed


def extract_features(fighter_a, fighter_b) -> np.ndarray:
    """Extract feature vector from two Fighter objects.

    Returns 12-dimensional vector of stat differences (A - B).
    """
    def safe(val):
        return val if val and val > 0 else 0.0

    features = [
        # Record-based
        fighter_a.win_rate - fighter_b.win_rate,
        fighter_a.recent_form - fighter_b.recent_form,
        fighter_a.finish_rate - fighter_b.finish_rate,
        # Striking
        safe(fighter_a.sig_strikes_landed_per_min) - safe(fighter_b.sig_strikes_landed_per_min),
        safe(fighter_a.sig_strike_accuracy) - safe(fighter_b.sig_strike_accuracy),
        safe(fighter_a.sig_strike_defense) - safe(fighter_b.sig_strike_defense),
        # Absorbed (lower is better, so B - A)
        safe(fighter_b.sig_strikes_absorbed_per_min) - safe(fighter_a.sig_strikes_absorbed_per_min),
        # Grappling
        safe(fighter_a.takedown_avg) - safe(fighter_b.takedown_avg),
        safe(fighter_a.takedown_defense) - safe(fighter_b.takedown_defense),
        safe(fighter_a.submission_avg) - safe(fighter_b.submission_avg),
        # Physical
        safe(fighter_a.reach_inches) - safe(fighter_b.reach_inches),
        # Age advantage (younger is generally better in peak range)
        _age_advantage(fighter_a.age) - _age_advantage(fighter_b.age),
    ]
    return np.array(features, dtype=np.float64).reshape(1, -1)


def _age_advantage(age: int) -> float:
    """Convert age to advantage score (peak 28-32)."""
    if age <= 0:
        return 0.5
    if age < 25:
        return 0.85
    if age <= 32:
        return 1.0
    if age <= 35:
        return 0.9
    if age <= 38:
        return 0.75
    return 0.6


def predict_ml(fighter_a, fighter_b) -> float | None:
    """Predict probability of fighter A winning using ML model.

    Returns None if model not ready or fighter data insufficient.
    """
    if not _model_ready or _model is None:
        return None

    # Skip if both fighters have estimated data (low quality)
    if fighter_a.is_estimated and fighter_b.is_estimated:
        return None

    try:
        features = extract_features(fighter_a, fighter_b)
        # Check for all-zero features (no useful data)
        if np.all(np.abs(features) < 0.001):
            return None
        prob = _model.predict_proba(features)[0][1]  # P(fighter_a wins)
        return float(prob)
    except Exception as e:
        logger.warning(f"ML prediction failed: {e}")
        return None


def _parse_sherdog_past_event_urls(html: str, limit: int = 5) -> list[str]:
    """Return recent past UFC event URLs from the Sherdog org page HTML."""
    import re
    from datetime import datetime
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    events: list[tuple[datetime, str]] = []
    for table in soup.find_all("table", class_="new_table"):
        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 2:
                continue
            link = None
            for c in (tds[1:] + tds[:1]):
                a = c.find("a", href=lambda h: h and "/events/" in h)
                if a:
                    link = a
                    break
            if not link:
                continue
            date_text = tds[0].get_text(" ", strip=True)
            m = re.search(r"([A-Za-z]{3,9})\s+(\d{1,2})\s*,?\s*(\d{4})", date_text)
            if not m:
                continue
            try:
                d = datetime.strptime(f"{m.group(1)[:3]} {m.group(2)} {m.group(3)}", "%b %d %Y")
            except ValueError:
                continue
            if d >= today:
                continue
            href = link.get("href", "")
            full = ("https://www.sherdog.com" + href) if href.startswith("/") else href
            events.append((d, full))
    events.sort(reverse=True)
    return [u for _, u in events[:limit]]


def _parse_sherdog_past_event_results(html: str) -> list[tuple[str, str, int]]:
    """Return list of (fighter_a, fighter_b, winner) from a Sherdog past event page.

    winner = 1 if fighter_a won, 0 if fighter_b won. Draws/NC are skipped.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    results: list[tuple[str, str, int]] = []

    def _strip_outcome(text: str) -> tuple[str, str]:
        """Remove trailing 'win' / 'loss' / 'draw' / 'nc' token."""
        t = text.strip()
        lower = t.lower()
        for tok in (" win", " loss", " draw", " nc"):
            if lower.endswith(tok):
                return t[: -len(tok)].strip(), tok.strip()
        return t, ""

    # Main event from fight_card div
    main = soup.find("div", class_="fight_card")
    if main:
        lefts = main.find_all(class_="left_side")
        rights = main.find_all(class_="right_side")
        if lefts and rights:
            a_name_tag = lefts[0].find("span", itemprop="name") or lefts[0].find("a") or lefts[0]
            b_name_tag = rights[0].find("span", itemprop="name") or rights[0].find("a") or rights[0]
            a_name = a_name_tag.get_text(" ", strip=True) if a_name_tag else ""
            b_name = b_name_tag.get_text(" ", strip=True) if b_name_tag else ""
            # Determine winner by looking for "win" class or label
            left_text = lefts[0].get_text(" ", strip=True).lower()
            right_text = rights[0].get_text(" ", strip=True).lower()
            if a_name and b_name:
                if "win" in left_text and "loss" in right_text:
                    results.append((a_name, b_name, 1))
                elif "loss" in left_text and "win" in right_text:
                    results.append((a_name, b_name, 0))

    # Subevents
    for row in soup.find_all("tr", itemprop="subEvent"):
        tds = row.find_all("td")
        if len(tds) < 4:
            continue
        a_text = tds[1].get_text(" ", strip=True)
        b_text = tds[3].get_text(" ", strip=True)
        a_name, a_outcome = _strip_outcome(a_text)
        b_name, b_outcome = _strip_outcome(b_text)
        if not a_name or not b_name:
            continue
        if a_outcome == "win" and b_outcome == "loss":
            results.append((a_name, b_name, 1))
        elif a_outcome == "loss" and b_outcome == "win":
            results.append((a_name, b_name, 0))

    return results


async def train_model_from_history():
    """Train model from past UFC events scraped from Sherdog.

    Flow:
    1. Try loading pre-trained model from repo (survives redeploys)
    2. Fetch Sherdog UFC org page → pick last 5 past events
    3. For each event, fetch the page and parse (fighter_a, fighter_b, winner)
    4. Look up each fighter via Sherdog (search_rizin_fighter works for UFC too)
    5. Build feature matrix and fit logistic regression
    6. Save model to disk (committed to repo for redeploys)

    ufcstats.com is blocked from Render so this path intentionally avoids it.
    """
    global _model, _model_ready, _training_status

    _training_status = "loading"
    if os.path.exists(_MODEL_FILE):
        try:
            _model = joblib.load(_MODEL_FILE)
            _model_ready = True
            _training_status = "ready"
            logger.info("Loaded existing ML model from disk")
            return
        except Exception as e:
            logger.warning(f"Failed to load saved model: {e}")

    _training_status = "training"
    logger.info("Training ML model from Sherdog UFC history...")

    try:
        from app.services.rizin_scraper import (
            fetch_page,
            search_rizin_fighter,
            UFC_SHERDOG_URL,
        )

        org_html = await fetch_page(UFC_SHERDOG_URL)
        event_urls = _parse_sherdog_past_event_urls(org_html, limit=5)
        logger.info(f"Training on {len(event_urls)} past events")

        X_data: list[list[float]] = []
        y_data: list[int] = []

        # Sherdog lists the winner on the left side of every past fight row,
        # so raw scraped rows are 100% class-1. To prevent class imbalance,
        # randomly swap fighter order on half the samples (which flips the label).
        import random
        rng = random.Random(42)

        for event_url in event_urls:
            try:
                event_html = await fetch_page(event_url)
                results = _parse_sherdog_past_event_results(event_html)
                for a_name, b_name, winner in results:
                    try:
                        fa = await search_rizin_fighter(a_name)
                        fb = await search_rizin_fighter(b_name)
                    except Exception:
                        continue
                    if fa and fb and fa.sig_strikes_landed_per_min > 0 and fb.sig_strikes_landed_per_min > 0:
                        if rng.random() < 0.5:
                            features = extract_features(fb, fa)
                            y = 1 - winner
                        else:
                            features = extract_features(fa, fb)
                            y = winner
                        X_data.append(features[0].tolist())
                        y_data.append(y)
                    await asyncio.sleep(0.05)
            except Exception as e:
                logger.debug(f"Skipping event for training: {e}")
                continue

        if len(X_data) < 10:
            logger.warning(f"Insufficient training data ({len(X_data)} fights), skipping ML training")
            _training_status = "failed"
            return

        X = np.array(X_data)
        y = np.array(y_data)

        model = LogisticRegression(
            C=1.0,
            max_iter=1000,
            class_weight="balanced",
            solver="lbfgs",
        )
        model.fit(X, y)

        os.makedirs(_MODEL_DIR, exist_ok=True)
        joblib.dump(model, _MODEL_FILE)

        _model = model
        _model_ready = True
        _training_status = "ready"
        logger.info(f"ML model trained on {len(X)} fights (training accuracy: {model.score(X, y):.0%})")

    except Exception as e:
        _training_status = "failed"
        logger.error(f"ML model training failed: {e}")


def get_model_status() -> dict:
    return {"ready": _model_ready, "status": _training_status}


def is_model_ready() -> bool:
    return _model_ready
