"""Backup prediction history from Render to the repo.

`/api/predictions/export` の内容を `backend/data/prediction_history.json`
に書き出す。ワークフロー側で diff があればコミット＆push する。
Render再デプロイ時にこのファイルが読み込まれるので永続化される。
"""
import json
import os
import sys
import time
from urllib.request import Request, urlopen

API_BASE = os.environ.get("API_BASE", "https://fight-predict-api.onrender.com")
OUT_PATH = os.environ.get("OUT_PATH", "backend/data/prediction_history.json")
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


def main():
    data = fetch_json(f"{API_BASE}/api/predictions/export")
    if not isinstance(data, list):
        print(f"予期しないレスポンス型: {type(data).__name__}", file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"書き出し完了: {OUT_PATH} ({len(data)}件)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
