import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# --- Core AI ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "YOUR_KEY_HERE")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1135413860")
TELEGRAM_BUSINESS_CONNECTION_ID = os.getenv("TELEGRAM_BUSINESS_CONNECTION_ID")  # Optional: for Telegram Business

# --- Instagram / Meta ---
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")     # Page Access Token from Meta Graph API
IG_PAGE_ID = os.getenv("IG_PAGE_ID")               # Facebook Page ID linked to Instagram Business
FB_CLIENT_ID = os.getenv("FB_CLIENT_ID")
FB_CLIENT_SECRET = os.getenv("FB_CLIENT_SECRET")
FB_REDIRECT_URI = os.getenv("FB_REDIRECT_URI", "http://localhost:8000/auth/instagram/callback")

# --- Other Services ---
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# --- Startup Validation ---
_MOCK_MODE_WARNINGS = []

if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "YOUR_KEY_HERE":
    _MOCK_MODE_WARNINGS.append("ANTHROPIC_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    _MOCK_MODE_WARNINGS.append("TELEGRAM_BOT_TOKEN")

if not IG_ACCESS_TOKEN:
    _MOCK_MODE_WARNINGS.append("IG_ACCESS_TOKEN (Instagram Direct — mock mode)")

if not IG_PAGE_ID:
    _MOCK_MODE_WARNINGS.append("IG_PAGE_ID (Instagram Direct — mock mode)")

if not TELEGRAM_BUSINESS_CONNECTION_ID:
    logger.debug("TELEGRAM_BUSINESS_CONNECTION_ID not set — Telegram Business features disabled.")

if _MOCK_MODE_WARNINGS:
    for key in _MOCK_MODE_WARNINGS:
        logger.warning(f"[CONFIG] Missing env var: {key}. Running in local/mock mode for this service.")
        print(f"WARNING: {key} is not set in .env")

def update_env_file(key: str, value: str):
    env_path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(env_path):
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")
        os.environ[key] = value
        return

    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            updated = True
            break

    if not updated:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append(f"{key}={value}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
        
    os.environ[key] = value
