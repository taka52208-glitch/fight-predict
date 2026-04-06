import math
from app.models.fighter import Fighter, Fight, Prediction


def _safe_ratio(a: float, b: float) -> tuple[float, float]:
    """Normalize two values to ratios that sum to 1."""
    total = a + b
    if total == 0:
        return 0.5, 0.5
    return a / total, b / total


def _sigmoid_spread(prob: float, strength: float = 2.0) -> float:
    """Push probability away from 0.5 using sigmoid-like spreading."""
    centered = prob - 0.5
    spread = 0.5 * math.tanh(centered * strength)
    return 0.5 + spread


def calculate_prediction(fighter_a: Fighter, fighter_b: Fighter, fight: Fight) -> Prediction:
    """Advanced prediction using weighted multi-factor analysis (v3: 17 factors).

    When either fighter has estimated stats (RIZIN), stat-based factors are
    weighted down and record-based factors are weighted up to compensate.
    """

    scores = {"a": 0.0, "b": 0.0}
    factors = []

    # If either fighter has estimated stats, reduce stat weights and boost record weights
    either_estimated = fighter_a.is_estimated or fighter_b.is_estimated
    # stat_scale < 1.0 reduces stat factor weights; record_boost > 1.0 increases record weights
    stat_scale = 0.6 if either_estimated else 1.0
    record_boost = 1.4 if either_estimated else 1.0

    # ===== 1. Win Rate (weight: 12%) =====
    wr_a = fighter_a.win_rate
    wr_b = fighter_b.win_rate
    ra, rb = _safe_ratio(wr_a, wr_b)
    w_wr = 12 * record_boost
    scores["a"] += ra * w_wr
    scores["b"] += rb * w_wr
    if abs(wr_a - wr_b) > 0.1:
        better = fighter_a.name if wr_a > wr_b else fighter_b.name
        factors.append(f"勝率: {better}が優位 ({max(wr_a, wr_b):.0%} vs {min(wr_a, wr_b):.0%})")

    # ===== 2. Recent Form - Last 5 fights (weight: 12%) =====
    form_a = fighter_a.recent_form
    form_b = fighter_b.recent_form
    ra, rb = _safe_ratio(form_a, form_b)
    w_rf = 12 * record_boost
    scores["a"] += ra * w_rf
    scores["b"] += rb * w_rf

    streak_a = fighter_a.recent_win_streak
    streak_b = fighter_b.recent_win_streak
    if abs(streak_a - streak_b) >= 2:
        if streak_a > streak_b:
            better, better_streak, worse_streak = fighter_a.name, streak_a, streak_b
        else:
            better, better_streak, worse_streak = fighter_b.name, streak_b, streak_a
        streak_desc_better = f"{better_streak}連勝中" if better_streak > 0 else f"{abs(better_streak)}連敗中" if better_streak < 0 else "直近引分"
        streak_desc_worse = f"{worse_streak}連勝中" if worse_streak > 0 else f"{abs(worse_streak)}連敗中" if worse_streak < 0 else "直近引分"
        factors.append(f"直近の調子: {better}が優位 ({streak_desc_better} vs {streak_desc_worse})")

    # ===== 3. Striking offense (weight: 10%) =====
    slpm_a = fighter_a.sig_strikes_landed_per_min
    slpm_b = fighter_b.sig_strikes_landed_per_min
    w_so = 10 * stat_scale
    if slpm_a + slpm_b > 0:
        ra, rb = _safe_ratio(slpm_a, slpm_b)
        scores["a"] += ra * w_so
        scores["b"] += rb * w_so
        if abs(slpm_a - slpm_b) > 1.5:
            better = fighter_a.name if slpm_a > slpm_b else fighter_b.name
            factors.append(f"打撃力: {better}が優位 ({max(slpm_a, slpm_b):.1f} vs {min(slpm_a, slpm_b):.1f} SLpM)")

    # ===== 4. Striking accuracy (weight: 6%) =====
    acc_a = fighter_a.sig_strike_accuracy
    acc_b = fighter_b.sig_strike_accuracy
    w_sa = 6 * stat_scale
    if acc_a + acc_b > 0:
        ra, rb = _safe_ratio(acc_a, acc_b)
        scores["a"] += ra * w_sa
        scores["b"] += rb * w_sa

    # ===== 5. Strike defense (weight: 8%) =====
    sdef_a = fighter_a.sig_strike_defense
    sdef_b = fighter_b.sig_strike_defense
    w_sd = 8 * stat_scale
    if sdef_a + sdef_b > 0:
        ra, rb = _safe_ratio(sdef_a, sdef_b)
        scores["a"] += ra * w_sd
        scores["b"] += rb * w_sd
        if abs(sdef_a - sdef_b) > 0.1:
            better = fighter_a.name if sdef_a > sdef_b else fighter_b.name
            factors.append(f"打撃防御: {better}が優位 ({max(sdef_a, sdef_b):.0%} vs {min(sdef_a, sdef_b):.0%})")

    # ===== 6. Damage absorption (weight: 5%) =====
    # Lower is better - invert for scoring
    sapm_a = fighter_a.sig_strikes_absorbed_per_min
    sapm_b = fighter_b.sig_strikes_absorbed_per_min
    w_da = 5 * stat_scale
    if sapm_a + sapm_b > 0:
        # Invert: lower absorption = better
        ra, rb = _safe_ratio(sapm_b, sapm_a)
        scores["a"] += ra * w_da
        scores["b"] += rb * w_da

    # ===== 7. Takedown offense (weight: 6%) =====
    td_a = fighter_a.takedown_avg
    td_b = fighter_b.takedown_avg
    w_to = 6 * stat_scale
    if td_a + td_b > 0:
        ra, rb = _safe_ratio(td_a, td_b)
        scores["a"] += ra * w_to
        scores["b"] += rb * w_to
        if abs(td_a - td_b) > 1.0:
            better = fighter_a.name if td_a > td_b else fighter_b.name
            factors.append(f"テイクダウン: {better}が優位 ({max(td_a, td_b):.1f} vs {min(td_a, td_b):.1f}/試合)")

    # ===== 8. Takedown defense (weight: 5%) =====
    tdd_a = fighter_a.takedown_defense
    tdd_b = fighter_b.takedown_defense
    w_td = 5 * stat_scale
    if tdd_a + tdd_b > 0:
        ra, rb = _safe_ratio(tdd_a, tdd_b)
        scores["a"] += ra * w_td
        scores["b"] += rb * w_td

    # ===== 9. Submission game (weight: 4%) =====
    sub_a = fighter_a.submission_avg
    sub_b = fighter_b.submission_avg
    w_sg = 4 * stat_scale
    if sub_a + sub_b > 0:
        ra, rb = _safe_ratio(sub_a, sub_b)
        scores["a"] += ra * w_sg
        scores["b"] += rb * w_sg
        if abs(sub_a - sub_b) > 0.5:
            better = fighter_a.name if sub_a > sub_b else fighter_b.name
            factors.append(f"サブミッション: {better}が優位 ({max(sub_a, sub_b):.1f} vs {min(sub_a, sub_b):.1f}/試合)")

    # ===== 10. Finish rate (weight: 4%) =====
    fr_a = fighter_a.finish_rate
    fr_b = fighter_b.finish_rate
    w_fr = 4 * record_boost
    if fr_a + fr_b > 0:
        ra, rb = _safe_ratio(fr_a, fr_b)
        scores["a"] += ra * w_fr
        scores["b"] += rb * w_fr

    # ===== 11. Style matchup bonus (weight: 4%) =====
    style_a = fighter_a.style
    style_b = fighter_b.style

    style_bonus_a = 0.0
    style_bonus_b = 0.0

    if style_a == "striker" and style_b == "grappler":
        # Striker vs Grappler: check TDD of striker
        if fighter_a.takedown_defense > 0.7:
            style_bonus_a = 0.6  # Good TDD striker has advantage
            factors.append(f"スタイル相性: {fighter_a.name}はストライカーでTD防御率{fighter_a.takedown_defense:.0%} → グラップラー相手に有利")
        else:
            style_bonus_b = 0.6  # Grappler can take down striker
            factors.append(f"スタイル相性: {fighter_b.name}はグラップラーで{fighter_a.name}のTD防御率が低い → 組技展開有利")
    elif style_a == "grappler" and style_b == "striker":
        if fighter_b.takedown_defense > 0.7:
            style_bonus_b = 0.6
            factors.append(f"スタイル相性: {fighter_b.name}はストライカーでTD防御率{fighter_b.takedown_defense:.0%} → グラップラー相手に有利")
        else:
            style_bonus_a = 0.6
            factors.append(f"スタイル相性: {fighter_a.name}はグラップラーで{fighter_b.name}のTD防御率が低い → 組技展開有利")

    ra, rb = _safe_ratio(0.5 + style_bonus_a, 0.5 + style_bonus_b)
    scores["a"] += ra * 4
    scores["b"] += rb * 4

    # ===== 12. Reach advantage (weight: 4%) =====
    reach_a = fighter_a.reach_inches
    reach_b = fighter_b.reach_inches
    if reach_a > 0 and reach_b > 0:
        reach_diff = reach_a - reach_b
        if abs(reach_diff) > 2:
            # Significant reach advantage
            reach_adv = min(abs(reach_diff) / 10, 0.3)  # Cap at 0.3 bonus
            if reach_diff > 0:
                scores["a"] += (0.5 + reach_adv) * 4
                scores["b"] += (0.5 - reach_adv) * 4
                factors.append(f"リーチ差: {fighter_a.name}が+{reach_diff:.1f}インチ有利")
            else:
                scores["a"] += (0.5 - reach_adv) * 4
                scores["b"] += (0.5 + reach_adv) * 4
                factors.append(f"リーチ差: {fighter_b.name}が+{abs(reach_diff):.1f}インチ有利")
        else:
            scores["a"] += 2.0
            scores["b"] += 2.0
    else:
        scores["a"] += 2.0
        scores["b"] += 2.0

    # ===== 13. Strength of Schedule - opponent quality (weight: 6%) =====
    sos_a = fighter_a.opponent_avg_win_rate
    sos_b = fighter_b.opponent_avg_win_rate
    if sos_a >= 0 and sos_b >= 0 and (sos_a + sos_b) > 0:
        ra, rb = _safe_ratio(sos_a, sos_b)
        scores["a"] += ra * 6
        scores["b"] += rb * 6
        if abs(sos_a - sos_b) > 0.08:
            better = fighter_a.name if sos_a > sos_b else fighter_b.name
            factors.append(f"対戦相手の質: {better}が優位 (相手の平均勝率 {max(sos_a, sos_b):.0%} vs {min(sos_a, sos_b):.0%})")
    else:
        scores["a"] += 3.0
        scores["b"] += 3.0

    # ===== 14. Age / Career phase (weight: 6%) =====
    age_a = fighter_a.age
    age_b = fighter_b.age
    if age_a > 0 and age_b > 0:
        # Peak around 28-32. Penalize >35, heavy penalty >38
        def _age_score(age: int) -> float:
            if age < 25:
                return 0.9  # still developing
            elif 25 <= age <= 32:
                return 1.0  # peak
            elif 33 <= age <= 35:
                return 0.92
            elif 36 <= age <= 38:
                return 0.80
            elif 39 <= age <= 41:
                return 0.68
            else:
                return 0.55
        as_a = _age_score(age_a)
        as_b = _age_score(age_b)
        ra, rb = _safe_ratio(as_a, as_b)
        scores["a"] += ra * 6
        scores["b"] += rb * 6
        if abs(age_a - age_b) >= 5:
            younger = fighter_a.name if age_a < age_b else fighter_b.name
            factors.append(f"年齢差: {younger}が若く有利 ({min(age_a, age_b)}歳 vs {max(age_a, age_b)}歳)")
        elif age_a >= 36 or age_b >= 36:
            if age_a >= 36 and age_b < 36:
                factors.append(f"年齢: {fighter_a.name}が{age_a}歳でパフォーマンス低下リスク")
            elif age_b >= 36 and age_a < 36:
                factors.append(f"年齢: {fighter_b.name}が{age_b}歳でパフォーマンス低下リスク")
    else:
        scores["a"] += 3.0
        scores["b"] += 3.0

    # ===== 15. Head-to-Head record (weight: 4%) =====
    h2h_a = fighter_a.head_to_head.get(fighter_b.name, {})
    h2h_b = fighter_b.head_to_head.get(fighter_a.name, {})
    # Deduplicate: each fight is counted from both perspectives, take the max
    a_wins_over_b = max(h2h_a.get("wins", 0), h2h_b.get("losses", 0))
    b_wins_over_a = max(h2h_a.get("losses", 0), h2h_b.get("wins", 0))

    if a_wins_over_b + b_wins_over_a > 0:
        ra, rb = _safe_ratio(a_wins_over_b, b_wins_over_a)
        scores["a"] += ra * 4
        scores["b"] += rb * 4
        if a_wins_over_b > b_wins_over_a:
            factors.append(f"直接対決: {fighter_a.name}が{a_wins_over_b}勝{b_wins_over_a}敗で有利")
        elif b_wins_over_a > a_wins_over_b:
            factors.append(f"直接対決: {fighter_b.name}が{b_wins_over_a}勝{a_wins_over_b}敗で有利")
    else:
        scores["a"] += 2.0
        scores["b"] += 2.0

    # ===== 16. Layoff / Ring rust (weight: 2%) =====
    from datetime import datetime
    def _layoff_months(date_str: str) -> float:
        if not date_str:
            return -1
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d")
            delta = datetime.today() - d
            return delta.days / 30.0
        except ValueError:
            return -1

    lay_a = _layoff_months(fighter_a.last_fight_date)
    lay_b = _layoff_months(fighter_b.last_fight_date)
    if lay_a >= 0 and lay_b >= 0:
        def _layoff_score(months: float) -> float:
            if months <= 6:
                return 1.0
            elif months <= 12:
                return 0.95
            elif months <= 18:
                return 0.85
            elif months <= 24:
                return 0.75
            else:
                return 0.65
        ls_a = _layoff_score(lay_a)
        ls_b = _layoff_score(lay_b)
        ra, rb = _safe_ratio(ls_a, ls_b)
        scores["a"] += ra * 2
        scores["b"] += rb * 2
        if abs(lay_a - lay_b) >= 12:
            if lay_a > lay_b:
                factors.append(f"ブランク: {fighter_a.name}が{lay_a:.0f}ヶ月空き、試合勘に懸念")
            else:
                factors.append(f"ブランク: {fighter_b.name}が{lay_b:.0f}ヶ月空き、試合勘に懸念")
    else:
        scores["a"] += 1.0
        scores["b"] += 1.0

    # ===== 17. Weight class change (weight: 2%) =====
    # Simple check: if previous_weight_class differs from current, slight penalty
    wc_penalty_a = 1.0
    wc_penalty_b = 1.0
    if fighter_a.previous_weight_class and fighter_a.previous_weight_class != fighter_a.weight_class:
        wc_penalty_a = 0.88
        factors.append(f"階級変更: {fighter_a.name}は{fighter_a.previous_weight_class}→{fighter_a.weight_class}で順応リスクあり")
    if fighter_b.previous_weight_class and fighter_b.previous_weight_class != fighter_b.weight_class:
        wc_penalty_b = 0.88
        factors.append(f"階級変更: {fighter_b.name}は{fighter_b.previous_weight_class}→{fighter_b.weight_class}で順応リスクあり")
    ra, rb = _safe_ratio(wc_penalty_a, wc_penalty_b)
    scores["a"] += ra * 2
    scores["b"] += rb * 2

    # ===== Normalize to probabilities =====
    total = scores["a"] + scores["b"]
    if total == 0:
        prob_a = 0.5
        prob_b = 0.5
    else:
        prob_a = scores["a"] / total
        prob_b = scores["b"] / total

    # Apply sigmoid spread to make predictions more decisive
    prob_a = _sigmoid_spread(prob_a, strength=3.0)
    prob_b = 1.0 - prob_a

    # ===== Determine confidence =====
    diff = abs(prob_a - prob_b)
    total_fights = (fighter_a.wins + fighter_a.losses + fighter_b.wins + fighter_b.losses)
    has_stats = (fighter_a.sig_strikes_landed_per_min > 0 and fighter_b.sig_strikes_landed_per_min > 0
                 and not either_estimated)
    has_age = fighter_a.age > 0 and fighter_b.age > 0
    has_sos = fighter_a.opponent_avg_win_rate >= 0 and fighter_b.opponent_avg_win_rate >= 0

    data_quality = 0
    if total_fights > 10:
        data_quality += 1
    if has_stats:
        data_quality += 1
    if has_age:
        data_quality += 1
    if has_sos:
        data_quality += 1

    if diff > 0.22 and data_quality >= 3:
        confidence = "HIGH"
    elif diff > 0.10 and data_quality >= 2:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    # ===== Predict fight method =====
    method = _predict_method(fighter_a, fighter_b)

    if either_estimated:
        if fighter_a.is_estimated and fighter_b.is_estimated:
            factors.append("※ 両選手のスタッツは戦績から推定（実データなし）。勝率・戦績を重視した予測です")
        elif fighter_a.is_estimated:
            factors.append(f"※ {fighter_a.name}のスタッツは戦績から推定。勝率・戦績を重視した予測です")
        else:
            factors.append(f"※ {fighter_b.name}のスタッツは戦績から推定。勝率・戦績を重視した予測です")
        # Lower confidence when using estimated data
        if confidence == "HIGH":
            confidence = "MEDIUM"

    if not factors:
        factors.append("両選手のスタッツが拮抗しています")

    return Prediction(
        fight=fight,
        fighter_a_name=fighter_a.name,
        fighter_b_name=fighter_b.name,
        fighter_a_win_prob=round(prob_a, 3),
        fighter_b_win_prob=round(prob_b, 3),
        confidence=confidence,
        factors=factors,
        method_prediction=method,
    )


def _predict_method(fighter_a: Fighter, fighter_b: Fighter) -> str:
    """Predict the most likely method of victory."""
    # Average KO rates
    ko_score = (fighter_a.ko_rate + fighter_b.ko_rate) / 2
    # Average sub rates
    sub_score = (fighter_a.sub_rate + fighter_b.sub_rate) / 2
    # Decision likelihood based on defense
    def_score = (fighter_a.sig_strike_defense + fighter_b.sig_strike_defense) / 2

    # Higher defense = more likely to go to decision
    dec_score = def_score * 0.5

    if ko_score > sub_score and ko_score > dec_score:
        return "KO/TKO"
    elif sub_score > ko_score and sub_score > dec_score:
        return "Submission"
    else:
        return "Decision"
