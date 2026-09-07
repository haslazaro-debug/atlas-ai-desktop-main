import os
import json
import asyncio
import logging
import feedparser
from bs4 import BeautifulSoup
import anthropic
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, TELEGRAM_BOT_TOKEN
import tools

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "recon_config.json")

# Global scheduler instance
scheduler = AsyncIOScheduler()

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading recon config: {e}")
        return {}

def save_config(config_data):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving recon config: {e}")

import time

def fetch_feed_sync(url: str, content_type: str = "rss"):
    items = []
    try:
        if content_type == "rss":
            feed = feedparser.parse(url)
            now = time.time()
            
            entries = feed.entries
            try:
                entries.sort(key=lambda x: time.mktime(x.published_parsed) if getattr(x, 'published_parsed', None) else 0, reverse=True)
            except Exception:
                pass
                
            for entry in entries:
                pub_time = getattr(entry, 'published_parsed', None)
                if pub_time:
                    try:
                        entry_time = time.mktime(pub_time)
                        if now - entry_time > 86400:
                            continue
                    except Exception:
                        pass
                        
                title = entry.get("title", "")
                link = entry.get("link", url)
                summary = entry.get("summary", "")
                if summary:
                    soup = BeautifulSoup(summary, "html.parser")
                    summary = soup.get_text(separator=" ", strip=True)
                items.append(f"- {title}\n  Источник: {link}\n  {summary}")
                if len(items) >= 10:
                    break
            
            if not items:
                for entry in entries[:5]:
                    title = entry.get("title", "")
                    link = entry.get("link", url)
                    summary = entry.get("summary", "")
                    if summary:
                        soup = BeautifulSoup(summary, "html.parser")
                        summary = soup.get_text(separator=" ", strip=True)
                    items.append(f"- {title}\n  Источник: {link}\n  {summary}")
                    
        logger.info(f"Fetched {len(items)} items from {url}")
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
    return "\n".join(items)

async def fetch_news_async():
    config = load_config()
    sources = config.get("sources", [])
    
    all_data = []
    for source in sources:
        name = source.get("name")
        url = source.get("url")
        ctype = source.get("type", "rss")
        
        data = await asyncio.to_thread(fetch_feed_sync, url, ctype)
        if data:
            all_data.append(f"Source: {name}\n{data}")
            
    return "\n\n".join(all_data)

async def generate_brief_async(raw_data: str) -> str:
    if not raw_data.strip():
        return "Не удалось собрать данные из источников за последние 24 часа."
        
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "YOUR_KEY_HERE":
        return "Ошибка: ANTHROPIC_API_KEY не настроен."
        
    config = load_config()
    focus_topic = config.get("focus_topic", "Общие новости технологий и бизнеса")
        
    prompt = f"""Ты аналитик. Ниже сырые новости из лент. Выбери из них ровно 3 самых свежих и важных события по теме '{focus_topic}'.

ИНСТРУКЦИЯ ПО ФИЛЬТРАЦИИ:
Игнорируй макроэкономику и поглощения корпораций, если они бесполезны для соло-разработчиков и криейторов. Отбирай только практические новости: обновления алгоритмов, монетизацию, новые полезные инструменты, тренды и кейсы заработка.

ИНСТРУКЦИЯ ПО ФОРМАТИРОВАНИЮ:
Категорически запрещено оборачивать ответ в markdown-блоки кода (```html ... ```) и генерировать структуру веб-страницы (<html>, <head>, <title>, <body>).
Ответ должен начинаться СРАЗУ с символа ⚡ и использовать только теги <b> и <i> для Telegram. Оформи строго в HTML без символов #, ##, **, *.

<b>⚡ ATLAS RECON // СВОДКА</b>
<i>Фокус: {focus_topic}</i>
───────────────────────

<b>1. [Заголовок события]</b>
• <b>Суть:</b> емко в 1-2 предложения.
• <b>Контекст:</b> почему это имеет значение.

───────────────────────
<i>Данные обновлены.</i>

Сырые новости:
{raw_data}
"""

    try:
        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"LLM generation error in recon dump: {e}")
        return f"Ошибка генерации брифа: {str(e)}"

async def run_recon_job(chat_id=None):
    logger.info("Running Recon Dump Job...")
    config = load_config()
    
    if not chat_id:
        chat_id = config.get("chat_id")
    if not chat_id:
        from config import TELEGRAM_CHAT_ID
        chat_id = TELEGRAM_CHAT_ID
        
    if not chat_id:
        logger.warning("No chat_id configured for recon dump. Cannot send brief.")
        return "Ошибка: chat_id не настроен. Не могу отправить бриф."
        
    raw_data = await fetch_news_async()
    brief = await generate_brief_async(raw_data)
    
    # Send via telegram API
    import requests
    from telegram_bot import format_to_tg_html
    if TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_TOKEN != "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        html_text = format_to_tg_html(brief)
        
        try:
            resp = requests.post(
                url,
                data={"chat_id": chat_id, "text": html_text, "parse_mode": "HTML"},
                timeout=15
            )
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send recon brief to telegram: {e}")
            
    return brief

def set_user_timezone(timezone_iana: str):
    try:
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(timezone_iana)
            
        except ImportError:
            import pytz
            pytz.timezone(timezone_iana)
    except Exception as e:
        logger.error(f"Invalid timezone {timezone_iana}: {e}")
        return False, f"Неверный формат часового пояса: {timezone_iana}"
        
    config = load_config()
    config["timezone"] = timezone_iana
    save_config(config)
    
    if config.get("is_enabled"):
        update_schedule(config.get("schedule_time", "09:00"), True)
        
    return True, f"Часовой пояс успешно изменен на {timezone_iana}"

def update_schedule(time_str: str, enabled: bool):
    config = load_config()
    config["schedule_time"] = time_str
    config["is_enabled"] = enabled
    save_config(config)
    
    # Reschedule
    job_id = "recon_dump_job"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        
    if enabled:
        try:
            hour, minute = map(int, time_str.split(":"))
            timezone = config.get("timezone", "Asia/Almaty")
            scheduler.add_job(
                run_recon_job,
                CronTrigger(hour=hour, minute=minute, timezone=timezone),
                id=job_id,
                replace_existing=True
            )
            logger.info(f"Scheduled recon dump at {time_str} ({timezone})")
        except Exception as e:
            logger.error(f"Error scheduling recon dump: {e}")
            return False, str(e)
            
    return True, "Success"

def get_current_schedule():
    return load_config()

def init_scheduler():
    config = load_config()
    if config.get("is_enabled"):
        time_str = config.get("schedule_time", "09:00")
        try:
            hour, minute = map(int, time_str.split(":"))
            timezone = config.get("timezone", "Asia/Almaty")
            scheduler.add_job(
                run_recon_job,
                CronTrigger(hour=hour, minute=minute, timezone=timezone),
                id="recon_dump_job",
                replace_existing=True
            )
        except Exception as e:
            logger.error(f"Init scheduler error: {e}")
    if not scheduler.running:
        scheduler.start()
