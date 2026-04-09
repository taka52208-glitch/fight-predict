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


async def train_model_from_history():
    """Train model from past UFC event results scraped from ufcstats.com.

    1. Try loading pre-trained model from repo (survives redeploys)
    2. If not found, train from scratch using 5 recent events (fast)
    3. Save to disk for next restart within same deploy
    """
    global _model, _model_ready, _training_status

    # Step 1: Load existing model (committed to repo or from previous run)
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

    # Step 2: Train from scratch (limited to 5 events for speed)
    _training_status = "training"
    logger.info("Training ML model from historical fight data (5 events)...")

    try:
        from app.services.ufc_scraper import search_fighter
        import httpx
        from bs4 import BeautifulSoup

        async with httpx.AsyncClient(
            timeout=20.0,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        ) as client:
            resp = await client.get("https://ufcstats.com/statistics/events/completed?page=all")
            if resp.status_code != 200:
                logger.warning("Failed to fetch completed events for training")
                _training_status = "failed"
                return

            soup = BeautifulSoup(resp.text, "lxml")
            event_links = []
            for row in soup.select("tr.b-statistics__table-row"):
                link = row.select_one("a")
                if link and link.get("href"):
                    event_links.append(link["href"].strip())

            # Only 5 events for fast startup (vs 30 before)
            event_links = event_links[:5]

            X_data = []
            y_data = []

            for event_url in event_links:
                try:
                    resp = await client.get(event_url)
                    if resp.status_code != 200:
                        continue

                    event_soup = BeautifulSoup(resp.text, "lxml")
                    fight_rows = event_soup.select("tr.b-fight-details__table-row.b-fight-details__table-row__hover")

                    for row in fight_rows:
                        fighter_links = row.select("a.b-link.b-fight-details__person-link")
                        if len(fighter_links) < 2:
                            continue

                        name_a = fighter_links[0].get_text(strip=True)
                        name_b = fighter_links[1].get_text(strip=True)

                        result_cells = row.select("td p.b-fight-details__table-text")
                        if not result_cells:
                            continue
                        result_text = result_cells[0].get_text(strip=True).upper()
                        if result_text == "W":
                            winner = 1
                        elif result_text == "L":
                            winner = 0
                        else:
                            continue

                        fa = await search_fighter(name_a)
                        fb = await search_fighter(name_b)

                        if fa and fb and fa.sig_strikes_landed_per_min > 0:
                            features = extract_features(fa, fb)
                            X_data.append(features[0])
                            y_data.append(winner)

                except Exception as e:
                    logger.debug(f"Skipping event for training: {e}")
                    continue

                await asyncio.sleep(0.05)

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

            # Save model
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
