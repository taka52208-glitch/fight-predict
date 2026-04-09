"""Prediction history tracker — stores predictions and tracks accuracy."""

import json
import logging
import os
import uuid
from datetime import datetime, timezone

from app.models.fighter import PredictionRecord, AccuracyStats, Prediction

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
_HISTORY_FILE = os.path.join(_DATA_DIR, "prediction_history.json")


def _ensure_data_dir():
    os.makedirs(_DATA_DIR, exist_ok=True)


def _load_history() -> list[dict]:
    if not os.path.exists(_HISTORY_FILE):
        return []
    try:
        with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load prediction history: {e}")
        return []


def _save_history(records: list[dict]):
    _ensure_data_dir()
    with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def save_prediction(prediction: Prediction, org: str) -> PredictionRecord:
    """Save a prediction to history and return the record."""
    prob_a = prediction.fighter_a_win_prob
    prob_b = prediction.fighter_b_win_prob
    predicted_winner = prediction.fighter_a_name if prob_a >= prob_b else prediction.fighter_b_name

    record = PredictionRecord(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.now(timezone.utc).isoformat(),
        fighter_a_name=prediction.fighter_a_name,
        fighter_b_name=prediction.fighter_b_name,
        fighter_a_win_prob=prob_a,
        fighter_b_win_prob=prob_b,
        predicted_winner=predicted_winner,
        confidence=prediction.confidence,
        method_prediction=prediction.method_prediction,
        organization=org.upper(),
    )

    history = _load_history()
    # Avoid duplicate: same fighters within 1 hour
    now = datetime.now(timezone.utc)
    for existing in history:
        if (existing.get("fighter_a_name") == record.fighter_a_name
                and existing.get("fighter_b_name") == record.fighter_b_name
                and existing.get("actual_winner") is None):
            try:
                ts = datetime.fromisoformat(existing["timestamp"])
                if (now - ts).total_seconds() < 3600:
                    return PredictionRecord(**existing)
            except (ValueError, KeyError):
                pass

    history.append(record.model_dump())
    _save_history(history)
    return record


def record_result(prediction_id: str, actual_winner: str) -> PredictionRecord | None:
    """Record the actual result of a fight."""
    history = _load_history()
    for rec in history:
        if rec.get("id") == prediction_id:
            rec["actual_winner"] = actual_winner
            rec["is_correct"] = (rec.get("predicted_winner", "").lower() == actual_winner.lower())
            _save_history(history)
            return PredictionRecord(**rec)
    return None


def get_accuracy_stats() -> AccuracyStats:
    """Calculate accuracy statistics from history."""
    history = _load_history()
    records = [PredictionRecord(**r) for r in history]

    resolved = [r for r in records if r.actual_winner is not None]
    total = len(resolved)
    correct = sum(1 for r in resolved if r.is_correct)

    by_confidence: dict[str, dict] = {}
    for level in ("HIGH", "MEDIUM", "LOW"):
        level_records = [r for r in resolved if r.confidence == level]
        level_total = len(level_records)
        level_correct = sum(1 for r in level_records if r.is_correct)
        if level_total > 0:
            by_confidence[level] = {
                "total": level_total,
                "correct": level_correct,
                "accuracy": round(level_correct / level_total, 3),
            }

    # Return most recent 20 records (resolved first, then pending)
    resolved_sorted = sorted(resolved, key=lambda r: r.timestamp, reverse=True)
    pending = sorted(
        [r for r in records if r.actual_winner is None],
        key=lambda r: r.timestamp, reverse=True,
    )
    recent = (resolved_sorted + pending)[:20]

    return AccuracyStats(
        total=total,
        correct=correct,
        accuracy=round(correct / total, 3) if total > 0 else 0.0,
        by_confidence=by_confidence,
        recent=recent,
    )


def get_pending_predictions() -> list[PredictionRecord]:
    """Get predictions that don't have results yet."""
    history = _load_history()
    pending = [PredictionRecord(**r) for r in history if r.get("actual_winner") is None]
    return sorted(pending, key=lambda r: r.timestamp, reverse=True)
