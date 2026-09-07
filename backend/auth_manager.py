import time
import json
import os
import requests
from fastapi import HTTPException
from typing import Dict, Optional
from pydantic import BaseModel

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

class AuthError(Exception):
    pass

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_settings(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

TIER_LIMITS = {
    "standard": {
        "model": "claude-haiku-4-5",
        "monthly_tokens": 5000000,
        "priority": False,
        "byok": False,
    },
    "pro": {
        "model": "claude-sonnet-5",
        "monthly_tokens": 8000000,
        "priority": False,
        "byok": False,
    },
    "business": {
        "model": "claude-sonnet-5",
        "monthly_tokens": 15000000,
        "priority": True,
        "byok": False,
    },
    "lifetime_standard": {
        "model": "any",
        "monthly_tokens": 0,
        "priority": False,
        "byok": True,
    },
    "lifetime_pro": {
        "model": "claude-sonnet-5",
        "monthly_tokens": 10000000, # 1-year boost pool
        "priority": True,
        "byok": True,
    }
}

class UserRateLimit(BaseModel):
    requests_this_minute: int = 0
    minute_window_start: float = 0.0

def send_telegram_alert(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=5)
    except Exception:
        pass

class AuthManager:
    def __init__(self):
        self.users: Dict[str, UserRateLimit] = {}
        # Hard limits for non-BYOK tiers to protect margin
        self.MAX_REQ_PER_MIN = 60

    def get_tier(self) -> str:
        data = load_settings()
        tier = data.get("tier", "free")
        if tier == "free":
            return "standard" # fallback to standard structure if free
        return tier

    def set_tier(self, tier: str):
        data = load_settings()
        data["tier"] = tier
        save_settings(data)

    def check_rate_limit(self, user_id: str = "local_user"):
        tier = self.get_tier()
        if tier.startswith("lifetime"):
            return # BYOK usually doesn't have local rate limit

        current_time = time.time()
        if user_id not in self.users:
            self.users[user_id] = UserRateLimit(minute_window_start=current_time)
            
        user_limit = self.users[user_id]
        if current_time - user_limit.minute_window_start >= 60:
            user_limit.requests_this_minute = 0
            user_limit.minute_window_start = current_time
            
        if user_limit.requests_this_minute >= self.MAX_REQ_PER_MIN:
            reset_in = int(60 - (current_time - user_limit.minute_window_start))
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again in {max(1, reset_in)}s",
                headers={"Retry-After": str(max(1, reset_in))}
            )
        user_limit.requests_this_minute += 1

    def get_llm_credentials(self, provider: str, requested_model: str):
        tier = self.get_tier()
        limits = TIER_LIMITS.get(tier, TIER_LIMITS["standard"])
        
        # Model escalation protection
        if not limits["byok"]:
            allowed_model = limits["model"]
            if allowed_model == "claude-haiku-4-5" and "sonnet" in requested_model.lower():
                raise AuthError("Твой тариф не включает эту модель — необходим апгрейд до Pro или Business")
                
        # In a real app, this would return actual keys. For ATLAS Desktop, keys are loaded from .env.
        return {"provider": provider, "model": requested_model, "priority": limits["priority"]}

    def record_token_usage(self, user_id: str, tier: str, tokens_used: int):
        limits = TIER_LIMITS.get(tier)
        if not limits or limits["monthly_tokens"] == 0:
            return # No quota to track (e.g., lifetime_standard)
            
        quota = limits["monthly_tokens"]
        data = load_settings()
        
        # Simple tracking for desktop (usually 1 user)
        current_usage = data.get("tokens_used", 0) + tokens_used
        data["tokens_used"] = current_usage
        
        # Check 80% threshold
        threshold = int(quota * 0.8)
        notified = data.get("quota_80_notified", False)
        
        if current_usage >= threshold and not notified:
            send_telegram_alert(f"⚠️ Внимание: Вы израсходовали 80% квоты токенов вашего тарифа {tier.upper()} ({current_usage}/{quota}).")
            data["quota_80_notified"] = True
            
        save_settings(data)

auth_manager = AuthManager()
