import os
import json
import sys
import urllib.request
from pathlib import Path

# Load from .env if present
ROOT = Path(__file__).resolve().parent.parent
env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
DEFAULT_CHAT = os.environ.get("TELEGRAM_SIGNALS_CHAT_ID", os.environ.get("TELEGRAM_CHAT_ID", "")).strip()

def send(text: str, chat_id: str = None) -> dict:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or TOKEN
    target_chat = chat_id or os.environ.get("TELEGRAM_SIGNALS_CHAT_ID", os.environ.get("TELEGRAM_CHAT_ID", "")).strip() or DEFAULT_CHAT
    if not bot_token or not target_chat:
        return {"ok": False, "error": "Credenciais do Telegram não configuradas no ambiente"}

    payload = json.dumps(
        {"chat_id": target_chat, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "BotradeClient"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main() -> int:
    if len(sys.argv) > 1:
        text = sys.argv[1]
    else:
        text = sys.stdin.read()
    try:
        result = send(text)
        print("ok" if result.get("ok") else result)
        return 0 if result.get("ok") else 1
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
