"""Daily X post drafts → Gmail.

朝8時JST実行。直近7日以内の大会について X投稿下書きを生成して
自分宛てにメール送信する。Gmail SMTP。依存は stdlib のみ。
"""
import json
import os
import smtplib
import ssl
import sys
import time
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.parse import quote
from urllib.request import Request, urlopen

API_BASE = os.environ.get("API_BASE", "https://fight-predict-api.onrender.com")
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT = os.environ.get("RECIPIENT") or GMAIL_USER

WINDOW_DAYS = 7
FULL_CARD_WITHIN_DAYS = 2
# Renderが再デプロイ直後は選手キャッシュが空で24選手のスクレイプに最大10分弱かかる。
TIMEOUT = 900
RETRIES = 2


def fetch_json(url: str):
    last_err = None
    for attempt in range(RETRIES + 1):
        try:
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            last_err = e
            if attempt < RETRIES:
                print(f"fetch失敗 (attempt {attempt + 1}/{RETRIES + 1}): {e} → 30秒後リトライ")
                time.sleep(30)
    raise last_err


def parse_event_date(s: str):
    return datetime.strptime(s, "%b %d %Y").date()


def build_sections(today, events):
    sections = []
    for ev in events:
        try:
            event_date = parse_event_date(ev["date"])
        except (ValueError, KeyError):
            continue
        days_ahead = (event_date - today).days
        if not (0 <= days_ahead <= WINDOW_DAYS):
            continue

        org = (ev.get("organization") or "UFC").lower()
        url = ev["url"]
        header = f"## {ev['name']}\n{ev['date']} (あと{days_ahead}日 / {ev.get('organization', '?')})"

        try:
            posts = fetch_json(
                f"{API_BASE}/api/generate/x-posts?event_url={quote(url, safe=':/')}&org={org}"
            )
        except Exception as e:
            sections.append((days_ahead, f"{header}\n\n[生成失敗: {e}]"))
            continue

        if days_ahead > FULL_CARD_WITHIN_DAYS:
            main_only = [p for p in posts if p.get("type") == "main"]
            posts = main_only or posts[:1]

        body_parts = []
        for i, p in enumerate(posts, 1):
            label = p.get("type", "post")
            body_parts.append(f"--- [{i}/{len(posts)}] {label} ---\n{p['text']}")
        sections.append((days_ahead, f"{header}\n\n" + "\n\n".join(body_parts)))

    sections.sort(key=lambda x: x[0])
    return [s for _, s in sections]


def send_email(subject: str, body: str):
    msg = EmailMessage()
    msg["From"] = GMAIL_USER
    msg["To"] = RECIPIENT
    msg["Subject"] = subject
    msg.set_content(body)
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)


def main():
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst).date()

    events = fetch_json(f"{API_BASE}/api/events/upcoming?org=all")
    sections = build_sections(today, events)

    if not sections:
        print(f"[{today}] 投稿対象なし（今後{WINDOW_DAYS}日以内に大会なし）。メールスキップ。")
        return 0

    body = (
        f"🥊 X投稿下書き {today.isoformat()} (JST)\n"
        f"対象大会: {len(sections)}件\n"
        f"\n投稿時は1日1〜2本に分散推奨。ハッシュタグは適宜整理してください。\n"
        f"\n================================\n\n"
        + "\n\n================================\n\n".join(sections)
    )
    subject = f"X投稿下書き {today.isoformat()} ({len(sections)}大会)"
    send_email(subject, body)
    print(f"[{today}] メール送信完了 → {RECIPIENT} ({len(sections)}大会)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
