"""X (Twitter) Bot poster — OAuth 1.0a で POST /2/tweets を叩く共通モジュール.

GitHub Actions 上で各 generate_*.py から呼び出される。`X_BOT_ENABLED=true` の
ときだけ実投稿し、それ以外は noop（Gmail 経由の半自動運用が継続）。

環境変数:
    X_BOT_ENABLED          : "true" のときだけ投稿する。未設定 or その他は noop。
    X_API_KEY              : Consumer Key (OAuth1)
    X_API_SECRET           : Consumer Secret (OAuth1)
    X_ACCESS_TOKEN         : Access Token (OAuth1)
    X_ACCESS_TOKEN_SECRET  : Access Token Secret (OAuth1)

依存: requests, requests-oauthlib（GitHub Actions 側で pip install）。
"""
from __future__ import annotations

import os
import sys
from typing import Optional


def is_enabled() -> bool:
    return os.environ.get("X_BOT_ENABLED", "").lower() == "true"


def _missing_secrets() -> list[str]:
    required = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]
    return [k for k in required if not os.environ.get(k)]


def post_tweet(text: str) -> Optional[dict]:
    """X に1件投稿する。

    戻り値: 成功時は X API のレスポンス dict、無効化中は None。
    投稿に失敗した場合は例外を上げる（呼び出し側で握って Gmail だけ送る運用）。
    """
    if not is_enabled():
        print("[x_poster] X_BOT_ENABLED != true → スキップ（Gmail のみ送信）")
        return None

    missing = _missing_secrets()
    if missing:
        raise RuntimeError(f"[x_poster] 必須シークレット未設定: {missing}")

    if not text or not text.strip():
        raise ValueError("[x_poster] 空文字は投稿できません")

    if len(text) > 280:
        # 念のため切り詰め（report_generator 側で 280 に収めているはずだが二重防御）
        print(f"[x_poster] 280文字超過({len(text)}) → 末尾切り詰め")
        text = text[:277] + "…"

    try:
        import requests
        from requests_oauthlib import OAuth1
    except ImportError as e:
        raise RuntimeError(
            "[x_poster] requests / requests-oauthlib が未インストール。"
            "ワークフロー側で pip install してください。"
        ) from e

    auth = OAuth1(
        os.environ["X_API_KEY"],
        os.environ["X_API_SECRET"],
        os.environ["X_ACCESS_TOKEN"],
        os.environ["X_ACCESS_TOKEN_SECRET"],
    )
    resp = requests.post(
        "https://api.twitter.com/2/tweets",
        json={"text": text},
        auth=auth,
        timeout=30,
    )
    if resp.status_code != 201:
        raise RuntimeError(
            f"[x_poster] 投稿失敗 status={resp.status_code} body={resp.text[:300]}"
        )
    data = resp.json()
    tweet_id = data.get("data", {}).get("id")
    print(f"[x_poster] 投稿成功 id={tweet_id} ({len(text)}文字)")
    return data


def try_post(text: str, label: str = "") -> tuple[bool, str]:
    """投稿を試みて (成功フラグ, 状態説明文字列) を返す。例外は内部で握る。

    label は Gmail 本文に状態行を載せるとき用のラベル（任意）。
    """
    if not is_enabled():
        return False, "X_BOT_ENABLED=false（Gmail のみ）"
    try:
        result = post_tweet(text)
        tweet_id = result.get("data", {}).get("id") if result else None
        return True, f"X投稿成功 id={tweet_id}"
    except Exception as e:
        msg = str(e)[:200]
        print(f"[x_poster] {label} 投稿失敗: {msg}", file=sys.stderr)
        return False, f"X投稿失敗: {msg}"
