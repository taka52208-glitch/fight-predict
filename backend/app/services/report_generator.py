"""Generate note articles and X (Twitter) posts from event predictions."""

from app.models.fighter import Prediction, Fighter


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

    # Main post (thread starter)
    main_lines = [f"🥊 {event_name} AI全試合予測", ""]
    for pred in predictions[:5]:  # first 5 in main post
        pct_a = round(pred.fighter_a_win_prob * 100)
        pct_b = round(pred.fighter_b_win_prob * 100)
        winner = pred.fighter_a_name if pct_a >= pct_b else pred.fighter_b_name
        winner_pct = max(pct_a, pct_b)
        emoji = _confidence_emoji(pred.confidence)
        main_lines.append(f"{emoji} {pred.fighter_a_name} vs {pred.fighter_b_name}")
        main_lines.append(f"→ {winner} {winner_pct}% ({pred.confidence})")
        main_lines.append("")

    main_lines.append("全カード詳細予測はこちら👇")
    main_lines.append("https://fight-predict-takas-projects-de61dd0f.vercel.app")
    main_lines.append("")

    # Hashtags
    event_tag = event_name.replace(" ", "").replace(":", "")
    org_tags = {"UFC": "#UFC #MMA", "RIZIN": "#RIZIN #格闘技"}.get(org, "#MMA")
    main_lines.append(f"#{event_tag} {org_tags} #FightPredict")

    posts.append({
        "text": "\n".join(main_lines),
        "type": "main",
    })

    # Individual card posts (for thread replies or separate posts)
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

        card_lines.append(f"#{event_tag} {org_tags} #FightPredict")

        posts.append({
            "text": "\n".join(card_lines),
            "type": "card",
        })

    return posts
