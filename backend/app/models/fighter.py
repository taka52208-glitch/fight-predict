from pydantic import BaseModel


class Fighter(BaseModel):
    name: str
    nickname: str = ""
    record: str = ""  # "20-5-0"
    wins: int = 0
    losses: int = 0
    draws: int = 0
    ko_wins: int = 0
    sub_wins: int = 0
    dec_wins: int = 0
    height: str = ""
    reach: str = ""
    weight_class: str = ""
    age: int = 0
    stance: str = ""
    organization: str = ""  # "UFC" or "RIZIN"
    sig_strikes_landed_per_min: float = 0.0
    sig_strike_accuracy: float = 0.0
    sig_strikes_absorbed_per_min: float = 0.0
    sig_strike_defense: float = 0.0
    takedown_avg: float = 0.0
    takedown_accuracy: float = 0.0
    takedown_defense: float = 0.0
    submission_avg: float = 0.0
    # New fields for improved prediction
    recent_win_streak: int = 0  # current win/loss streak (negative = loss streak)
    recent_fights: list[str] = []  # last 5 results: ["W", "W", "L", "W", "W"]
    reach_inches: float = 0.0  # parsed numeric reach
    height_inches: float = 0.0  # parsed numeric height
    style: str = ""  # "striker", "grappler", "balanced"
    # v3 fields
    last_fight_date: str = ""  # "YYYY-MM-DD" or raw date string
    opponent_avg_win_rate: float = -1.0  # avg win rate of past opponents (-1 = unknown)
    head_to_head: dict[str, dict] = {}  # {opponent_name: {"wins": N, "losses": N}}
    previous_weight_class: str = ""  # previous weight class if changed
    is_estimated: bool = False  # True if stats are estimated (not scraped from real data)

    @property
    def win_rate(self) -> float:
        total = self.wins + self.losses + self.draws
        if total == 0:
            return 0.0
        return self.wins / total

    @property
    def ko_rate(self) -> float:
        if self.wins == 0:
            return 0.0
        return self.ko_wins / self.wins

    @property
    def sub_rate(self) -> float:
        if self.wins == 0:
            return 0.0
        return self.sub_wins / self.wins

    @property
    def finish_rate(self) -> float:
        if self.wins == 0:
            return 0.0
        return (self.ko_wins + self.sub_wins) / self.wins

    @property
    def recent_form(self) -> float:
        """Recent form score: weighted average of last 5 fights (most recent = heaviest)."""
        if not self.recent_fights:
            return 0.5
        weights = [5, 4, 3, 2, 1]  # most recent fight weighted highest
        total_weight = 0
        score = 0.0
        for i, result in enumerate(self.recent_fights):
            w = weights[i] if i < len(weights) else 1
            total_weight += w
            if result == "W":
                score += w
            elif result == "D":
                score += w * 0.5
        return score / total_weight if total_weight > 0 else 0.5


class Fight(BaseModel):
    event_name: str = ""
    event_date: str = ""
    fighter_a: str = ""
    fighter_b: str = ""
    weight_class: str = ""
    organization: str = ""  # "UFC" or "RIZIN"


class Prediction(BaseModel):
    fight: Fight
    fighter_a_name: str
    fighter_b_name: str
    fighter_a_win_prob: float
    fighter_b_win_prob: float
    confidence: str = ""  # "HIGH", "MEDIUM", "LOW"
    factors: list[str] = []
    method_prediction: str = ""  # "KO/TKO", "Submission", "Decision"


class PredictionRecord(BaseModel):
    id: str = ""
    timestamp: str = ""
    fighter_a_name: str
    fighter_b_name: str
    fighter_a_win_prob: float
    fighter_b_win_prob: float
    predicted_winner: str = ""
    confidence: str = ""
    method_prediction: str = ""
    organization: str = ""
    # 結果 (後から記録)
    actual_winner: str | None = None
    is_correct: bool | None = None


class AccuracyStats(BaseModel):
    total: int = 0
    correct: int = 0
    accuracy: float = 0.0
    by_confidence: dict[str, dict] = {}  # {"HIGH": {"total": N, "correct": N, "accuracy": 0.X}}
    recent: list[PredictionRecord] = []
