"""Weekly accuracy stats X post → Gmail.

毎週月曜朝8時JSTに `/api/generate/weekly-stats` を叩き、X投稿用の下書きを
Gmailへ送信する。結果が1件もない週はスキップ。依存は stdlib のみ。
"""
import json
import os
import smtplib
import ssl
import sys
import time
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.request import Request, urlopen

import x_poster  # noqa: E402  同ディレクトリ内モジュール

API_BASE = os.environ.get("API_BASE", "https://fight-predict-api.onrender.com")
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT = os.environ.get("RECIPIENT") or GMAIL_USER

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

    post = fetch_json(f"{API_BASE}/api/generate/weekly-stats")

    if post.get("total", 0) == 0 or not post.get("text"):
        print(f"[{today}] 的中記録なし。メールスキップ。")
        return 0

    text = post["text"]
    posted, status = x_poster.try_post(text, label="weekly-stats")
    status_line = f"[{status}]\n" if status else ""

    body = (
        f"📊 週次的中サマリー {today.isoformat()} (JST)\n"
        f"累計的中数: {post['total']}件\n"
        f"{status_line}"
        f"\n以下をそのままXに投稿してください（X投稿成功時は確認用）。\n"
        f"\n================================\n\n"
        f"{text}"
    )
    subject = f"週次的中サマリー {today.isoformat()}"
    send_email(subject, body)
    print(f"[{today}] メール送信完了 → {RECIPIENT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
