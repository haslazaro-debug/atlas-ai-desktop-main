import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"

import shutil
import asyncio
import uuid
import json
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from telegram_bot import start_bot
from agent_core import execute_command
from voice_engine import transcribe_audio
from tts_engine import generate_speech, stream_audio_generator
import tempfile
from sales_engine import save_business_document
from fastapi.responses import StreamingResponse
from fastapi import Request
import stripe
import requests
from auth_manager import auth_manager, load_settings, save_settings
from config import STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY, STRIPE_WEBHOOK_SECRET, TELEGRAM_BOT_TOKEN
from config import IG_ACCESS_TOKEN, IG_PAGE_ID, TELEGRAM_BUSINESS_CONNECTION_ID
from fastapi.responses import Response as FastAPIResponse
from ai_brain import generate_sales_response

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)
import urllib.parse
from fastapi.responses import RedirectResponse

async def safe_start_bot():
    try:
        await start_bot()
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start Telegram Bot in the background
    asyncio.create_task(safe_start_bot())
    
    # Test Anthropic connection
    from config import ANTHROPIC_API_KEY
    if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "YOUR_KEY_HERE":
        print("[CLAUDE STATUS: READY]")
    else:
        print("[CLAUDE STATUS: NOT CONFIGURED]")
    from skills.recon_dump import init_scheduler, scheduler
    init_scheduler()

    yield
    
    if scheduler.running:
        scheduler.shutdown()
    # Shutdown logic could go here

app = FastAPI(title="ATLAS Backend", lifespan=lifespan)

app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CommandRequest(BaseModel):
    command: str
    mode: str = "text"
    image: str = None

@app.post("/api/command")
async def api_command(request: CommandRequest):
    if not request.command or not request.command.strip():
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="command_text не может быть пустым")
        
    cmd_lower = request.command.lower()
    if any(word in cmd_lower for word in ["бриф", "recon", "дайджест", "сводк"]):
        try:
            from skills.recon_dump import run_recon_job
            brief_text = await run_recon_job()
            audio_url = await generate_speech("Свежий бриф собран и выведен на экран.")
            return {
                "text": brief_text,
                "response": brief_text,
                "status": "success",
                "audio": audio_url,
                "requires_confirmation": False,
                "action_type": None,
                "error": None
            }
        except Exception as e:
            return {"text": None, "response": None, "status": "error", "audio": None, "requires_confirmation": False, "action_type": None, "error": str(e)}

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, execute_command, request.command, request.mode, request.image)
        text_resp = result.get("text", "Done") if isinstance(result, dict) else result
        requires_confirmation = result.get("requires_confirmation", False) if isinstance(result, dict) else False
        action_type = result.get("action_type", None) if isinstance(result, dict) else None
        
        audio_url = await generate_speech(text_resp)
        
        return {
            "text": text_resp,
            "response": text_resp,
            "status": "success",
            "audio": audio_url,
            "requires_confirmation": requires_confirmation,
            "action_type": action_type,
            "error": None
        }
    except Exception as e:
        return {"text": None, "response": None, "status": "error", "audio": None, "requires_confirmation": False, "action_type": None, "error": str(e)}

@app.post("/api/transcribe")
async def api_transcribe(audio: UploadFile = File(...)):
    file_path = None
    try:
        content = await audio.read()
        logger.info(f"[AUDIO RECEIVED]: filename={audio.filename}, size={len(content)} bytes, content_type={audio.content_type}")
        
        if len(content) < 1000:
            logger.warning("[AUDIO WARNING]: получен подозрительно маленький файл, возможно запись не удалась")
            raise HTTPException(status_code=400, detail="Audio file too small")
            
        _, ext = os.path.splitext(audio.filename or "")
        file_path = os.path.join(BASE_DIR, f"temp_frontend_{uuid.uuid4().hex}{ext or '.webm'}")
        with open(file_path, "wb") as buffer:
            buffer.write(content)
            
        loop = asyncio.get_event_loop()
        transcription = await loop.run_in_executor(None, transcribe_audio, file_path)
        
        return {
            "text": transcription,
            "success": bool(transcription and transcription.strip())
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[STT ERROR]: Transcription endpoint failed")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

@app.post("/api/voice")
async def api_voice(audio: UploadFile = File(...), mode: str = Form("text"), image: str = Form(None)):
    file_path = None
    try:
        _, ext = os.path.splitext(audio.filename or "")
        file_path = os.path.join(BASE_DIR, f"temp_frontend_{uuid.uuid4().hex}{ext or '.webm'}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)
            
        loop = asyncio.get_event_loop()
        transcription = await loop.run_in_executor(None, transcribe_audio, file_path)
        
        if not transcription or not transcription.strip():
            return {"text": "Речь не распознана, попробуйте снова", "audio": None, "error": None}
            
        result = await loop.run_in_executor(None, execute_command, transcription, mode, image)
        text_resp = result.get("text", "Done") if isinstance(result, dict) else result
        audio_url = await generate_speech(text_resp)
        
        return {
            "text": text_resp,
            "audio": audio_url,
            "error": None
        }
    except Exception as e:
        return {"text": None, "audio": None, "error": str(e)}
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

@app.get("/api/status")
async def api_status():
    from config import ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN
    return {
        "status": "online",
        "keys": {
            "claude_configured": bool(ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "YOUR_KEY_HERE"),
            "telegram_configured": bool(TELEGRAM_BOT_TOKEN),
        }
    }

@app.get("/api/tts_stream")
async def api_tts_stream(text: str):
    return StreamingResponse(stream_audio_generator(text), media_type="audio/mpeg")

@app.get("/api/user/tier")
async def api_user_tier():
    return {"tier": auth_manager.get_tier()}

class CheckoutRequest(BaseModel):
    plan: str

@app.post("/api/create-checkout-session")
async def create_checkout_session(req: CheckoutRequest):
    try:
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        if not stripe.api_key:
            logger.warning("STRIPE_SECRET_KEY is missing.")
            return {"error": "Stripe key not configured"}
            
        plan_configs = {
            "standard": {"name": "ATLAS Standard Subscription", "amount": 2900, "recurring": True},
            "pro": {"name": "ATLAS Pro Subscription", "amount": 9900, "recurring": True},
            "business": {"name": "ATLAS Business Subscription", "amount": 18900, "recurring": True},
            "lifetime_standard": {"name": "ATLAS Lifetime Standard (BYOK)", "amount": 34900, "recurring": False},
            "lifetime_pro": {"name": "ATLAS Lifetime Pro (Includes Managed Boost)", "amount": 59900, "recurring": False},
        }
        
        cfg = plan_configs.get(req.plan)
        if not cfg:
            logger.error(f"Invalid plan selected: {req.plan}")
            return {"error": f"Invalid plan: {req.plan}"}
            
        price_data = {
            "currency": "usd",
            "product_data": {"name": cfg["name"]},
            "unit_amount": cfg["amount"]
        }
        if cfg["recurring"]:
            price_data["recurring"] = {"interval": "month"}
            
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': price_data,
                'quantity': 1,
            }],
            mode='subscription' if cfg["recurring"] else 'payment',
            success_url="http://localhost:5173/?success=true",
            cancel_url="http://localhost:5173/?canceled=true",
            metadata={"plan_type": req.plan}
        )
        return {"url": session.url}
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        return {"error": str(e)}

@app.post("/api/stripe-webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        plan_type = session.get('metadata', {}).get('plan_type', 'pro')
        new_tier = "lifetime" if plan_type == "lifetime" else "pro"
        auth_manager.set_tier(new_tier)
        logger.info(f"User tier updated to {new_tier}")
        
    return {"status": "success"}

@app.get("/api/telegram/check")
async def telegram_check():
    if not TELEGRAM_BOT_TOKEN:
        return {"status": "error", "message": "Bot token not configured"}
    try:
        resp = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe", timeout=5)
        data = resp.json()
        if data.get("ok"):
            return {"status": "success", "bot": data["result"]}
        else:
            return {"status": "error", "message": "Invalid token"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/telegram/pair")
async def telegram_pair():
    if not TELEGRAM_BOT_TOKEN:
        return {"status": "error", "url": None}
    try:
        resp = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe", timeout=5)
        data = resp.json()
        if data.get("ok"):
            bot_username = data["result"]["username"]
            return {"status": "success", "url": f"https://t.me/{bot_username}?start=auth"}
    except Exception:
        pass
    return {"status": "error", "url": None}

class SettingsPayload(BaseModel):
    volume: int = None
    chime: bool = None
    voice_notes: bool = None

@app.get("/api/settings")
async def get_settings():
    return load_settings()

@app.post("/api/settings")
async def update_settings(payload: SettingsPayload):
    data = load_settings()
    if payload.volume is not None:
        data["volume"] = payload.volume
    if payload.chime is not None:
        data["chime"] = payload.chime
    if payload.voice_notes is not None:
        data["voice_notes"] = payload.voice_notes
    save_settings(data)
    return {"status": "success"}


# ---------------------------------------------------------------------------
# MESSAGING HELPERS
# ---------------------------------------------------------------------------

def send_telegram_message(chat_id: str, text: str) -> None:
    """Send a message to any chat via Telegram Bot API."""
    if not text:
        return
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("[send_telegram_message] TELEGRAM_BOT_TOKEN not set — skipping.")
        return
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=5
        )
        if not resp.ok:
            logger.warning(f"[send_telegram_message] API error for {chat_id}: {resp.text}")
    except Exception as e:
        logger.error(f"[send_telegram_message] Failed: {e}")

ESCALATIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "escalations_log.json")

def log_escalation(business_id: str, customer_id: str, client_message: str, ai_reason: str):
    """Сохраняет информацию об эскалации в локальный JSON-файл."""
    record = {
        "timestamp": datetime.now().isoformat(),
        "business_id": business_id,
        "customer_id": customer_id,
        "message": client_message,
        "reason": ai_reason,
        "status": "pending"  # pending / resolved
    }
    
    data = []
    if os.path.exists(ESCALATIONS_FILE):
        try:
            with open(ESCALATIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = []
            
    data.append(record)
    
    with open(ESCALATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def notify_business_owner(business_id: str, customer_id: str, client_message: str, ai_reply: str) -> None:
    """
    Notifies the business owner when ATLAS escalates.
    Owner chat ID is resolved from OWNER_CHAT_{business_id} env var,
    with fallback to DEFAULT_OWNER_CHAT (or TELEGRAM_CHAT_ID).
    """
    owner_chat_id = (
        os.getenv(f"OWNER_CHAT_{business_id}")
        or os.getenv("DEFAULT_OWNER_CHAT")
        or os.getenv("TELEGRAM_CHAT_ID", "")
    )
    if not owner_chat_id:
        logger.warning(f"[notify_owner] No owner chat configured for business={business_id}")
        return

    text = (
        "[ESCALATION] ATLAS needs you!\n\n"
        f"Business: {business_id}\n"
        f"Client ID: {customer_id}\n"
        f"Client message: {client_message}\n\n"
        f"ATLAS reply sent: {ai_reply[:200]}{'...' if len(ai_reply) > 200 else ''}\n\n"
        "Please respond to the client directly."
    )
    send_telegram_message(owner_chat_id, text)
    log_escalation(business_id, customer_id, client_message, ai_reply)
    logger.info(f"[notify_owner] Escalation alert sent to owner ({owner_chat_id}) for business={business_id}")


# ---------------------------------------------------------------------------
# TELEGRAM BUSINESS WEBHOOK
# ---------------------------------------------------------------------------

@app.post("/webhook/telegram")
async def telegram_business_webhook(request: Request):
    """Receives Telegram Business messages, generates a sales reply via ATLAS, and auto-sends it."""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if "business_message" in data:
        message = data["business_message"]
        chat_id = str(message.get("chat", {}).get("id", ""))
        text = message.get("text", "").strip()
        connection_id = data.get("business_connection_id", "")
        business_id = connection_id or "default_telegram_biz"

        logger.info(f"[Telegram Business] chat_id={chat_id} biz={business_id}: {text!r}")

        if text and chat_id:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, generate_sales_response, business_id, chat_id, text
            )
            sales_reply = result.get("reply", "")
            status = result.get("status", "auto_reply")
            logger.info(f"[Telegram Business] status={status} chat_id={chat_id}")

            # Always send the reply to the client
            send_telegram_message(chat_id, sales_reply)

            # Escalate to owner if needed
            if status == "escalate_to_human":
                notify_business_owner(business_id, chat_id, text, sales_reply)

    return {"status": "ok"}



# ---------------------------------------------------------------------------
# INSTAGRAM DIRECT WEBHOOK
# ---------------------------------------------------------------------------

IG_VERIFY_TOKEN = "atlas_secure_verify_token"

@app.get("/webhook/instagram")
async def verify_instagram_webhook(request: Request):
    """Meta webhook verification handshake."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge", "")

    if mode == "subscribe" and token == IG_VERIFY_TOKEN:
        logger.info("[Instagram] Webhook verified successfully.")
        return FastAPIResponse(content=challenge, media_type="text/plain")
    logger.warning(f"[Instagram] Webhook verification failed. mode={mode}, token={token!r}")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@app.post("/webhook/instagram")
async def instagram_direct_webhook(request: Request):
    """Receives Instagram Direct messages, generates a sales reply via ATLAS, and auto-sends it."""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if data.get("object") == "instagram":
        business_id = IG_PAGE_ID or "default_ig_biz"

        for entry in data.get("entry", []):
            for messaging in entry.get("messaging", []):
                sender_id = str(messaging.get("sender", {}).get("id", ""))
                message_text = messaging.get("message", {}).get("text", "").strip()

                if not message_text or not sender_id:
                    continue

                logger.info(f"[Instagram Direct] sender={sender_id}: {message_text!r}")

                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, generate_sales_response, business_id, sender_id, message_text
                )
                sales_reply = result.get("reply", "")
                status = result.get("status", "auto_reply")
                logger.info(f"[Instagram Direct] status={status} sender={sender_id}")

                # Send reply via Meta Graph API
                if IG_ACCESS_TOKEN and IG_PAGE_ID and sales_reply:
                    try:
                        resp = requests.post(
                            f"https://graph.facebook.com/v19.0/{IG_PAGE_ID}/messages",
                            json={
                                "recipient": {"id": sender_id},
                                "message": {"text": sales_reply},
                                "access_token": IG_ACCESS_TOKEN
                            },
                            timeout=10
                        )
                        if resp.ok:
                            logger.info(f"[Instagram Direct] Reply sent to {sender_id}.")
                        else:
                            logger.warning(f"[Instagram Direct] Meta API error: {resp.text}")
                    except Exception as e:
                        logger.error(f"[Instagram Direct] Failed to send reply: {e}")

                # Escalate to owner if needed
                if status == "escalate_to_human" and sales_reply:
                    notify_business_owner(business_id, sender_id, message_text, sales_reply)

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# INSTAGRAM OAUTH INTEGRATION
# ---------------------------------------------------------------------------

@app.get("/api/instagram/status")
async def api_instagram_status():
    from config import IG_ACCESS_TOKEN, IG_PAGE_ID
    if IG_ACCESS_TOKEN and IG_PAGE_ID:
        return {"status": "connected", "page_id": IG_PAGE_ID}
    return {"status": "idle"}

@app.get("/api/instagram/auth-url")
async def api_instagram_auth_url():
    import os
    import urllib.parse
    from dotenv import load_dotenv
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)
    
    client_id = os.getenv("FB_CLIENT_ID")
    redirect_uri = os.getenv("FB_REDIRECT_URI", "http://localhost:8000/auth/instagram/callback")
    
    if not client_id or not client_id.strip():
        return {"error": "Meta App credentials missing in backend/.env"}
    
    scope = "instagram_basic,instagram_manage_messages,pages_show_list,pages_manage_metadata"
    url = (
        f"https://www.facebook.com/v18.0/dialog/oauth?"
        f"client_id={client_id.strip()}&redirect_uri={urllib.parse.quote(redirect_uri.strip())}&scope={scope}&response_type=code"
    )
    return {"url": url}

@app.get("/auth/instagram/callback")
async def auth_instagram_callback(code: str = None, error: str = None):
    import os
    import httpx
    from dotenv import load_dotenv
    from config import update_env_file
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)
    
    client_id = os.getenv("FB_CLIENT_ID")
    client_secret = os.getenv("FB_CLIENT_SECRET")
    redirect_uri = os.getenv("FB_REDIRECT_URI", "http://localhost:8000/auth/instagram/callback")
    
    if error or not code:
        return RedirectResponse(url="http://localhost:8080/?ig_auth=error")

    if not client_id or not client_secret:
        return RedirectResponse(url="http://localhost:8080/?ig_auth=missing_credentials")
        
    try:
        async with httpx.AsyncClient() as client:
            token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
            response = await client.get(token_url, params={
                "client_id": client_id.strip(),
                "client_secret": client_secret.strip(),
                "redirect_uri": redirect_uri.strip(),
                "code": code
            })
            
            if response.status_code != 200:
                logger.error(f"Failed to get token: {response.text}")
                return RedirectResponse(url="http://localhost:8080/?ig_auth=error")
            
            data = response.json()
            user_access_token = data.get("access_token")
            
            pages_response = await client.get("https://graph.facebook.com/v18.0/me/accounts", params={
                "access_token": user_access_token
            })
            
            if pages_response.status_code != 200:
                logger.error("Failed to fetch user pages")
                return RedirectResponse(url="http://localhost:8080/?ig_auth=error")
            
            pages_data = pages_response.json().get("data", [])
            if not pages_data:
                logger.error("No Facebook pages found for this user")
                return RedirectResponse(url="http://localhost:8080/?ig_auth=no_pages")

            page = pages_data[0]
            page_id = page["id"]
            page_access_token = page["access_token"]
            
            ig_response = await client.get(f"https://graph.facebook.com/v18.0/{page_id}", params={
                "fields": "instagram_business_account",
                "access_token": page_access_token
            })
            
            ig_data = ig_response.json()
            instagram_business_account_id = ig_data.get("instagram_business_account", {}).get("id")

            if not instagram_business_account_id:
                logger.error("No Instagram Business Account linked to this Facebook page")
                return RedirectResponse(url="http://localhost:8080/?ig_auth=no_ig_linked")
            
            update_env_file("IG_ACCESS_TOKEN", page_access_token)
            update_env_file("IG_PAGE_ID", instagram_business_account_id)
            
            import config
            config.IG_ACCESS_TOKEN = page_access_token
            config.IG_PAGE_ID = instagram_business_account_id
            
            return RedirectResponse(url="http://localhost:8080/?instagram_connected=true")
            
    except Exception as e:
        logger.error(f"OAuth Callback Error: {e}")
        return RedirectResponse(url="http://localhost:8080/?ig_auth=error")

# ---------------------------------------------------------------------------
# BUSINESS KNOWLEDGE UPLOAD
# ---------------------------------------------------------------------------

@app.post("/business/{business_id}/upload")
async def upload_business_document(business_id: str, file: UploadFile = File(...)):
    """
    Эндпоинт для загрузки документов базы знаний бизнеса (Excel, CSV, TXT).
    Файл сразу сохраняется в папку бизнеса и начинает использоваться ИИ-мозгом.
    """
    try:
        # Создаем временный файл для обработки входящего потока
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        # Передаем воркеру сохранения из sales_engine
        saved_path = save_business_document(business_id, tmp_path, file.filename)
        
        # Удаляем временный файл
        os.unlink(tmp_path)
        
        logger.info(f"📁 Успешно загружен файл {file.filename} для бизнеса {business_id}")
        return {
            "status": "success",
            "filename": file.filename,
            "business_id": business_id,
            "message": "Документ успешно добавлен в базу знаний ИИ-продажника."
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки файла для бизнеса {business_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Не удалось сохранить файл: {str(e)}")
