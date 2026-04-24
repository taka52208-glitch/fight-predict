"""Hit-log (AI予測 vs 実結果) X post drafts → Gmail.

毎朝8時JST実行。直近3日以内に終了したイベントを Sherdog から拾い、
`/api/generate/hit-log` で予測の自動解決＋投稿下書きを生成して Gmail に送る。
X投稿可能な下書き（text が空でない）だけをメール本文に含める。
依存は stdlib のみ。
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

WINDOW_DAYS = 3
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

    events = fetch_json(f"{API_BASE}/api/events/recent?org=all&days={WINDOW_DAYS}")
    if not events:
        print(f"[{today}] 直近{WINDOW_DAYS}日以内に終了した大会なし。スキップ。")
        return 0

    sections: list[str] = []
    for ev in events:
        url = ev.get("url")
        if not url:
            continue
        try:
            post = fetch_json(f"{API_BASE}/api/generate/hit-log?event_url={quote(url, safe=':/')}")
        except Exception as e:
            print(f"hit-log生成失敗 {ev.get('name')}: {e}")
            continue

        if not post.get("text"):
            # 解決済み予測が1件もない（このツールで予測保存していなかった大会等）
            print(f"[{today}] {ev.get('name')} → 投稿対象なし（予測履歴なし）")
            continue

        header = (
            f"## {ev.get('name', '')}\n"
            f"{ev.get('date', '')} ({ev.get('organization', '?')}) | "
            f"{post.get('correct', 0)}/{post.get('total', 0)}的中 "
            f"／今回新規解決: {post.get('resolved_this_run', 0)}件"
        )
        sections.append(f"{header}\n\n{post['text']}")

    if not sections:
        print(f"[{today}] 送信可能な的中ログなし。スキップ。")
        return 0

    body = (
        f"🎯 的中ログ下書き {today.isoformat()} (JST)\n"
        f"対象大会: {len(sections)}件\n"
        f"\nそのままXに投稿してください。\n"
        f"\n================================\n\n"
        + "\n\n================================\n\n".join(sections)
    )
    subject = f"的中ログ下書き {today.isoformat()} ({len(sections)}大会)"
    send_email(subject, body)
    print(f"[{today}] メール送信完了 → {RECIPIENT} ({len(sections)}大会)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
