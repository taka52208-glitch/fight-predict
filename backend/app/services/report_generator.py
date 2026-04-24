"""Generate note articles and X (Twitter) posts from event predictions."""

from app.models.fighter import Prediction, Fighter, AccuracyStats, PredictionRecord

SITE_URL = "https://fight-predict-takas-projects-de61dd0f.vercel.app"


def _confidence_emoji(conf: str) -> str:
    return {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "⚪"}.get(conf, "⚪")


def _bar(pct: int, length: int = 20) -> str:
    filled = round(pct / 100 * length)
    return "█" * filled + "░" * (length - filled)


def generate_note_article(
    event_name: str,
    predictions: list[Prediction],
    fighters: list[tuple[Fighter | None, Fighter | None]],
    accuracy_pct: float | None = None,
) -> dict:
    """Generate a note article in markdown format.

    Returns {"title": str, "free_section": str, "paid_section": str, "full": str}
    """
    org = predictions[0].fight.organization if predictions else "UFC"
    date = predictions[0].fight.event_date if predictions else ""

    title = f"【AI分析】{event_name} 全{len(predictions)}試合 勝敗予測レポート"

    # --- Free section (visible to everyone) ---
    free_lines = [
        f"# {title}",
        "",
        f"> AIが17項目のスタッツ＋機械学習モデルで分析した、{event_name}の全試合予測です。",
        "",
    ]

    if accuracy_pct is not None and accuracy_pct > 0:
        free_lines.append(f"**過去の的中率: {accuracy_pct:.0%}**")
        free_lines.append("")

    free_lines.append("---")
    free_lines.append("")

    # Show first 2 fights for free (teaser)
    teaser_count = min(2, len(predictions))
    for i in range(teaser_count):
        pred = predictions[i]
        free_lines.extend(_format_fight_section(pred, fighters[i] if i < len(fighters) else (None, None), detailed=True))
        free_lines.append("")

    if len(predictions) > teaser_count:
        free_lines.extend([
            "---",
            "",
            f"**残り{len(predictions) - teaser_count}試合の予測は有料部分でご覧いただけます。**",
            "",
            "全カードの詳細分析（スタイル相性・年齢・ブランク・対戦相手の質）を含むフルレポートです。",
            "",
        ])

    # --- Paid section ---
    paid_lines = [
        "---",
        "",
        "## 全カード予測",
        "",
    ]

    for i in range(teaser_count, len(predictions)):
        pred = predictions[i]
        paid_lines.extend(_format_fight_section(pred, fighters[i] if i < len(fighters) else (None, None), detailed=True))
        paid_lines.append("")

    # Summary table
    paid_lines.extend([
        "---",
        "",
        "## まとめ：全試合予測一覧",
        "",
        "| 対戦 | 予測勝者 | 勝率 | 信頼度 | 決着 |",
        "|------|---------|------|--------|------|",
    ])

    for pred in predictions:
        pct_a = round(pred.fighter_a_win_prob * 100)
        pct_b = round(pred.fighter_b_win_prob * 100)
        if pct_a >= pct_b:
            winner, pct = pred.fighter_a_name, pct_a
        else:
            winner, pct = pred.fighter_b_name, pct_b
        paid_lines.append(
            f"| {pred.fighter_a_name} vs {pred.fighter_b_name} | **{winner}** | {pct}% | {pred.confidence} | {pred.method_prediction} |"
        )

    paid_lines.extend([
        "",
        "---",
        "",
        f"> この予測は [FIGHT PREDICT](https://fight-predict-takas-projects-de61dd0f.vercel.app) のAIが生成しました。",
        "> 17項目のスタッツ分析＋機械学習モデルによる予測です。",
        "",
    ])

    free_section = "\n".join(free_lines)
    paid_section = "\n".join(paid_lines)
    full = free_section + "\n" + paid_section

    return {
        "title": title,
        "free_section": free_section,
        "paid_section": paid_section,
        "full": full,
    }


def _format_fight_section(
    pred: Prediction,
    fighter_pair: tuple[Fighter | None, Fighter | None],
    detailed: bool = False,
) -> list[str]:
    """Format a single fight as markdown lines."""
    fa, fb = fighter_pair
    pct_a = round(pred.fighter_a_win_prob * 100)
    pct_b = round(pred.fighter_b_win_prob * 100)
    winner = pred.fighter_a_name if pct_a >= pct_b else pred.fighter_b_name
    conf = pred.confidence
    emoji = _confidence_emoji(conf)

    lines = [
        f"### {emoji} {pred.fighter_a_name} vs {pred.fighter_b_name}",
    ]

    if pred.fight.weight_class:
        lines.append(f"*{pred.fight.weight_class}*")

    lines.extend([
        "",
        f"**予測勝者: {winner}**",
        f"```",
        f"{pred.fighter_a_name}: {_bar(pct_a)} {pct_a}%",
        f"{pred.fighter_b_name}: {_bar(pct_b)} {pct_b}%",
        f"```",
        f"- 信頼度: **{conf}**",
        f"- 予想決着: **{pred.method_prediction}**",
        "",
    ])

    if detailed and fa and fb:
        lines.extend([
            "| スタッツ | " + fa.name.split()[-1] + " | " + fb.name.split()[-1] + " |",
            "|---------|------|------|",
            f"| 戦績 | {fa.record} | {fb.record} |",
            f"| 勝率 | {fa.win_rate:.0%} | {fb.win_rate:.0%} |",
            f"| 打撃/分 | {fa.sig_strikes_landed_per_min:.1f} | {fb.sig_strikes_landed_per_min:.1f} |",
            f"| 打撃防御 | {fa.sig_strike_defense:.0%} | {fb.sig_strike_defense:.0%} |",
            f"| TD/試合 | {fa.takedown_avg:.1f} | {fb.takedown_avg:.1f} |",
            f"| TD防御 | {fa.takedown_defense:.0%} | {fb.takedown_defense:.0%} |",
            "",
        ])

    # Factors (skip notes starting with ※)
    real_factors = [f for f in pred.factors if not f.startswith("※")]
    if real_factors:
        lines.append("**分析ポイント:**")
        for f in real_factors:
            lines.append(f"- {f}")
        lines.append("")

    return lines


def generate_x_posts(
    event_name: str,
    predictions: list[Prediction],
) -> list[dict]:
    """Generate X (Twitter) post texts for an event.

    Returns list of {"text": str, "type": "main"|"card"|"thread_end"}
    """
    org = predictions[0].fight.organization if predictions else "UFC"
    posts = []

    # X無料は280文字制限。メイン投稿は必ず収めるため絞り込む。
    display_name = event_name.split(" - ")[0]
    org_tags = {"UFC": "#UFC #MMA", "RIZIN": "#RIZIN #格闘技"}.get(org, "#MMA")

    def _last(name: str) -> str:
        return name.split()[-1] if " " in name else name

    # Main post: 信頼度の高い上位3試合のみ、苗字表記
    conf_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    sorted_preds = sorted(predictions, key=lambda p: conf_order.get(p.confidence, 3))

    main_lines = [f"🥊 {display_name} AI予測", ""]
    for pred in sorted_preds[:3]:
        pct_a = round(pred.fighter_a_win_prob * 100)
        pct_b = round(pred.fighter_b_win_prob * 100)
        winner = pred.fighter_a_name if pct_a >= pct_b else pred.fighter_b_name
        winner_pct = max(pct_a, pct_b)
        emoji = _confidence_emoji(pred.confidence)
        main_lines.append(
            f"{emoji} {_last(pred.fighter_a_name)} vs {_last(pred.fighter_b_name)} → {_last(winner)} {winner_pct}%"
        )

    main_lines.append("")
    main_lines.append("全試合詳細👇")
    main_lines.append("https://fight-predict-takas-projects-de61dd0f.vercel.app")
    main_lines.append("")
    main_lines.append(f"{org_tags} #FightPredict")

    posts.append({
        "text": "\n".join(main_lines),
        "type": "main",
    })

    # 個別カード投稿はフルネーム（1試合1投稿なので文字数余裕あり）
    for pred in predictions:
        pct_a = round(pred.fighter_a_win_prob * 100)
        pct_b = round(pred.fighter_b_win_prob * 100)
        winner = pred.fighter_a_name if pct_a >= pct_b else pred.fighter_b_name
        winner_pct = max(pct_a, pct_b)

        card_lines = [
            f"🥊 {pred.fighter_a_name} vs {pred.fighter_b_name}",
            "",
            f"AI予測: {winner} {winner_pct}%",
            f"信頼度: {pred.confidence} | 決着: {pred.method_prediction}",
            "",
        ]

        real_factors = [f for f in pred.factors if not f.startswith("※")]
        if real_factors:
            card_lines.append(real_factors[0])
            card_lines.append("")

        card_lines.append(f"{org_tags} #FightPredict")

        posts.append({
            "text": "\n".join(card_lines),
            "type": "card",
        })

    return posts


def generate_hit_log_post(event_name: str, records: list[PredictionRecord]) -> dict:
    """Generate an X post comparing AI predictions vs actual results for one event.

    `records` should be the already-resolved PredictionRecords for the event
    (actual_winner set). Posts stay under X's 280-char limit: if too long
    we drop individual fight lines starting from LOW-confidence fights.

    Returns {"text": str, "type": "hit_log", "total": int, "correct": int}.
    Returns text="" when records is empty so callers can skip sending.
    """
    if not records:
        return {"text": "", "type": "hit_log", "total": 0, "correct": 0}

    resolved = [r for r in records if r.actual_winner is not None]
    scored = [r for r in resolved if r.is_correct is not None and r.actual_winner not in ("DRAW", "NC")]
    total = len(scored)
    correct = sum(1 for r in scored if r.is_correct)

    org = records[0].organization if records else "UFC"
    org_tags = {"UFC": "#UFC #MMA", "RIZIN": "#RIZIN #格闘技"}.get(org, "#MMA")

    def _last(name: str) -> str:
        return name.split()[-1] if " " in name else name

    display_name = event_name.split(" - ")[0]
    acc_pct = round(correct / total * 100) if total > 0 else 0

    header = [
        f"🎯 {display_name} AI予測 vs 結果",
        "",
        f"的中 {correct}/{total} ({acc_pct}%)",
        "",
    ]

    # Build per-fight lines. Show correct ✅ first, then misses ❌.
    conf_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    sorted_resolved = sorted(
        resolved,
        key=lambda r: (0 if r.is_correct else 1, conf_order.get(r.confidence, 3)),
    )

    def _line(r: PredictionRecord) -> str:
        mark = "✅" if r.is_correct else ("❌" if r.actual_winner not in ("DRAW", "NC") else "➖")
        pct = round(max(r.fighter_a_win_prob, r.fighter_b_win_prob) * 100)
        if r.actual_winner in ("DRAW", "NC"):
            return f"{mark} {_last(r.fighter_a_name)} vs {_last(r.fighter_b_name)} → {r.actual_winner}"
        return f"{mark} {_last(r.predicted_winner)} {pct}%"

    footer = [
        "",
        "全予測履歴👇",
        SITE_URL,
        "",
        f"{org_tags} #FightPredict",
    ]

    # Iteratively drop trailing lines until under the 280-char X limit.
    fight_lines = [_line(r) for r in sorted_resolved]
    while True:
        text = "\n".join(header + fight_lines + footer)
        if len(text) <= 280 or not fight_lines:
            break
        fight_lines.pop()

    return {
        "text": text,
        "type": "hit_log",
        "total": total,
        "correct": correct,
    }


def generate_weekly_stats_post(stats: AccuracyStats) -> dict:
    """Generate an X post summarizing prediction accuracy.

    Returns {"text": str, "type": "weekly_stats", "total": int}.
    If there's no resolved prediction yet, returns a placeholder post
    so the caller can skip sending.
    """
    if stats.total == 0:
        return {
            "text": "",
            "type": "weekly_stats",
            "total": 0,
        }

    acc_pct = round(stats.accuracy * 100)
    lines = [
        "🥊 FIGHT PREDICT 的中実績アップデート",
        "",
        f"累計: {stats.correct}/{stats.total}的中 ({acc_pct}%)",
    ]

    for level in ("HIGH", "MEDIUM", "LOW"):
        data = stats.by_confidence.get(level)
        if not data:
            continue
        pct = round(data["accuracy"] * 100)
        label = {"HIGH": "🔴HIGH", "MEDIUM": "🟡MEDIUM", "LOW": "⚪LOW"}[level]
        lines.append(f"{label}: {data['correct']}/{data['total']} ({pct}%)")

    lines += [
        "",
        "次の大会予測はこちら👇",
        SITE_URL,
        "",
        "#UFC #MMA #RIZIN #FightPredict",
    ]

    return {
        "text": "\n".join(lines),
        "type": "weekly_stats",
        "total": stats.total,
    }
