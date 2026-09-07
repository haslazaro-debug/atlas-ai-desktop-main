import os
import asyncio
import logging
import re
import tempfile
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from voice_engine import transcribe_audio
from agent_core import execute_command
import agent_core
from ai_brain import generate_sales_response

async def cleanup_confirmation(context, chat_id, message_id):
    await asyncio.sleep(60)
    try:
        if agent_core.pending_action:
            agent_core.pending_action = None
            await context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)
            from skills.recon_dump import load_config
            lang = load_config().get("language", "Russian")
            msg = "Action cancelled (60s timeout)." if lang == "English" else "Действие отменено (таймаут 60с)."
            await context.bot.send_message(chat_id=chat_id, text=msg)
    except Exception:
        pass

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
        
    if query.data in ["lang_en", "lang_ru"]:
        from skills.recon_dump import load_config, save_config
        config = load_config()
        config["language"] = "English" if query.data == "lang_en" else "Russian"
        save_config(config)
        
        if query.data == "lang_en":
            await query.message.edit_text("⚡ ATLAS Online. Connection established.\n\nExecutive core active. What's the priority today?", reply_markup=None)
        else:
            await query.message.edit_text("⚡ ATLAS Online. Связь установлена.\n\nИсполнительный контур активен. Какая задача на повестке?", reply_markup=None)
        return

    command_text = "подтверждаю" if query.data == "confirm_action" else "отмена"
    await process_command(update, context, command_text, is_voice=False)

logger = logging.getLogger(__name__)

async def text_to_speech(text: str) -> str:
    try:
        temp_audio = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
        temp_audio.close()
        clean_text = re.sub(r'[*#_]', '', text).strip()
        
        process = await asyncio.create_subprocess_exec(
            "edge-tts", "--text", clean_text, "--write-media", temp_audio.name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        if process.returncode == 0 and os.path.exists(temp_audio.name) and os.path.getsize(temp_audio.name) > 0:
            return temp_audio.name
        else:
            if os.path.exists(temp_audio.name):
                os.remove(temp_audio.name)
            return None
    except Exception as e:
        logger.error(f"TTS Error: {e}")
        return None

async def fast_file_dispatch(context: ContextTypes.DEFAULT_TYPE, chat_id: int, command_text: str) -> bool:
    command_lower = command_text.lower()
    if "досье на" in command_lower or "отправь досье" in command_lower or "скинь" in command_lower:
        match = re.search(r"(?:досье на|скинь|отправь)\s+([a-zA-Zа-яА-Я0-9_ -]+)", command_lower)
        if match:
            company_raw = match.group(1).strip()
            import tools
            latest_file = tools.find_latest_desktop_file(company_raw, extension=".pdf")
            if latest_file:
                await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)
                with open(latest_file, 'rb') as doc:
                    await context.bot.send_document(
                        chat_id=chat_id, 
                        document=doc, 
                        caption=f"Файл найден: {os.path.basename(latest_file)}",
                        read_timeout=90,
                        write_timeout=90
                    )
                return True
    return False

async def keep_typing(context: ContextTypes.DEFAULT_TYPE, chat_id: int, action=ChatAction.TYPING):
    while True:
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=action)
            await asyncio.sleep(4)
        except asyncio.CancelledError:
            break
        except Exception:
            break

def ensure_chat_id_saved(chat_id):
    try:
        from skills.recon_dump import load_config, save_config
        config = load_config()
        if config.get("chat_id") != chat_id:
            config["chat_id"] = chat_id
            save_config(config)
    except Exception as e:
        logger.error(f"Error saving chat_id: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ensure_chat_id_saved(chat_id)
    msg = (
        "⚡ ATLAS Online. Connection established.\n\n"
        "Select your primary language for the executive core:"
    )
    keyboard = [
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(msg, reply_markup=reply_markup)

def format_to_tg_html(text: str) -> str:
    text = text.replace('###', '').replace('##', '').replace('#', '')
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    text = re.sub(r'^\s*-\s+', '• ', text, flags=re.MULTILINE)
    text = re.sub(r'```(?:html)?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</?(?:html|head|body|title)[^>]*>', '', text, flags=re.IGNORECASE)
    return text

async def safe_send_message(context, chat_id, text, reply_markup=None, photo_file=None, voice_file=None):
    html_text = format_to_tg_html(text)
    html_text = re.sub(r'```(.*?)```', r'<code>\1</code>', html_text, flags=re.DOTALL)
    html_text = re.sub(r'`(.*?)`', r'<code>\1</code>', html_text)
    
    try:
        if photo_file:
            return await context.bot.send_photo(chat_id=chat_id, photo=photo_file, caption=html_text, parse_mode="HTML", reply_markup=reply_markup)
        elif voice_file:
            return await context.bot.send_voice(chat_id=chat_id, voice=voice_file, caption=html_text, parse_mode="HTML", reply_markup=reply_markup)
        else:
            return await context.bot.send_message(chat_id=chat_id, text=html_text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"HTML parsing failed, falling back to plain text. Error: {e}")
        plain_text = re.sub(r'<[^>]+>', '', html_text)
        try:
            if photo_file:
                photo_file.seek(0)
                return await context.bot.send_photo(chat_id=chat_id, photo=photo_file, caption=plain_text, reply_markup=reply_markup)
            elif voice_file:
                voice_file.seek(0)
                return await context.bot.send_voice(chat_id=chat_id, voice=voice_file, caption=plain_text, reply_markup=reply_markup)
            else:
                return await context.bot.send_message(chat_id=chat_id, text=plain_text, reply_markup=reply_markup)
        except Exception:
            return await context.bot.send_message(chat_id=chat_id, text=plain_text, reply_markup=reply_markup)

async def process_command(update: Update, context: ContextTypes.DEFAULT_TYPE, command_text: str, is_voice: bool = False):
    chat_id = update.effective_chat.id
    ensure_chat_id_saved(chat_id)
    
    from skills.recon_dump import load_config
    lang = load_config().get("language", "Russian")
    agent_core.context_state["language"] = lang
    
    msg_accepted = "⚡ Task accepted, working..." if lang == "English" else "⚡ Принял задачу, работаю..."
    status_msg = await context.bot.send_message(chat_id, msg_accepted)
    heartbeat_task = asyncio.create_task(keep_typing(context, chat_id))
    
    try:
        import tools
        tools.TELEGRAM_CHAT_ID = chat_id

        if await fast_file_dispatch(context, chat_id, command_text):
            await status_msg.delete()
            return

        msg_analyzing = "⚡ Analyzing command and gathering data..." if lang == "English" else "⚡ Анализирую команду и собираю данные..."
        await status_msg.edit_text(msg_analyzing)
        result = await asyncio.to_thread(execute_command, command_text)
        
        if isinstance(result, dict):
            resp_text = result.get("text") or "Done."
            image_path = result.get("image_path")
            requires_confirm = result.get("requires_confirmation", False)
        else:
            resp_text = str(result)
            image_path = None
            requires_confirm = False
            
        await status_msg.delete()
        
        reply_markup = None
        if requires_confirm:
            btn_confirm = "✅ Confirm" if lang == "English" else "✅ Подтвердить"
            btn_cancel = "❌ Cancel" if lang == "English" else "❌ Отмена"
            keyboard = [
                [InlineKeyboardButton(btn_confirm, callback_data="confirm_action"),
                 InlineKeyboardButton(btn_cancel, callback_data="cancel_action")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        
        sent_msg = None
        if is_voice:
            ogg_path = await text_to_speech(resp_text)
            if ogg_path:
                try:
                    with open(ogg_path, "rb") as voice_file:
                        sent_msg = await safe_send_message(context, chat_id, resp_text, reply_markup=reply_markup, voice_file=voice_file)
                finally:
                    if os.path.exists(ogg_path):
                        os.remove(ogg_path)
            else:
                if image_path and os.path.exists(image_path):
                    with open(image_path, "rb") as photo_file:
                        sent_msg = await safe_send_message(context, chat_id, resp_text, reply_markup=reply_markup, photo_file=photo_file)
                else:
                    sent_msg = await safe_send_message(context, chat_id, resp_text, reply_markup=reply_markup)
        else:
            if image_path and os.path.exists(image_path):
                with open(image_path, "rb") as photo_file:
                    sent_msg = await safe_send_message(context, chat_id, resp_text, reply_markup=reply_markup, photo_file=photo_file)
            else:
                sent_msg = await safe_send_message(context, chat_id, resp_text, reply_markup=reply_markup)
                
        if requires_confirm and sent_msg:
            asyncio.create_task(cleanup_confirmation(context, chat_id, sent_msg.message_id))
                
    except Exception as e:
        logger.exception("Error processing command")
        err_msg = f"❌ Error: {str(e)}" if lang == "English" else f"❌ Ошибка: {str(e)}"
        await status_msg.edit_text(err_msg)
    finally:
        heartbeat_task.cancel()

async def unified_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    incoming_text = update.message.text
    
    if not incoming_text or not incoming_text.strip():
        return

    # 1. ЕСЛИ ЭТО ТЫ (ХОЗЯИН) -> ВЫПОЛНЯЕМ ЛИЧНЫЕ КОМАНДЫ (УПРАВЛЕНИЕ ПК)
    if user_id == str(TELEGRAM_CHAT_ID):
        await process_command(update, context, incoming_text, is_voice=False)
        return

    # 2. ЕСЛИ ЭТО КЛИЕНТ -> ВКЛЮЧАЕТСЯ ИИ-ПРОДАЖНИК ATLAS
    business_id = "default_business"
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, generate_sales_response, business_id, user_id, incoming_text
    )
    
    if result.get("reply"):
        await update.message.reply_text(result["reply"])
    
    if result.get("status") == "escalate_to_human":
        await context.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=f"🚨 *Эскалация для бизнеса!*\nКлиент: `{user_id}`\nЗапрос: {incoming_text}",
            parse_mode="Markdown"
        )

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    if not voice:
        return

    chat_id = update.effective_chat.id
    from skills.recon_dump import load_config
    lang = load_config().get("language", "Russian")
    msg_voice = "🎙️ Processing voice..." if lang == "English" else "🎙️ Обрабатываю голос..."
    status_msg = await context.bot.send_message(chat_id, msg_voice)
    heartbeat_task = asyncio.create_task(keep_typing(context, chat_id, ChatAction.RECORD_VOICE))
    
    file_path = f"temp_tg_voice_{voice.file_id}.ogg"
    
    try:
        file = await context.bot.get_file(voice.file_id, read_timeout=90)
        await file.download_to_drive(file_path)
        
        transcription = await asyncio.to_thread(transcribe_audio, file_path)
        
        if not transcription or not transcription.strip():
            msg_fail = "❌ Failed to recognize voice. Try again." if lang == "English" else "❌ Не удалось распознать голос. Попробуй ещё раз."
            await status_msg.edit_text(msg_fail)
            return

        await status_msg.delete()
        await process_command(update, context, transcription, is_voice=True)
            
    except Exception as e:
        logger.exception("Error processing voice message")
        err_msg = f"❌ Error: {str(e)}" if lang == "English" else f"❌ Ошибка: {str(e)}"
        await status_msg.edit_text(err_msg)
    finally:
        heartbeat_task.cancel()
        if os.path.exists(file_path):
            os.remove(file_path)

async def handle_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or len(args) < 3:
        await update.message.reply_text("Пример использования: /invoice ООО_Вектор 150000 Разработка_дизайна")
        return
        
    client_name = args[0].replace("_", " ")
    amount = args[1]
    service_description = " ".join(args[2:]).replace("_", " ")
    
    chat_id = update.effective_chat.id
    status_msg = await context.bot.send_message(chat_id, "⏳ Генерирую счет...")
    
    try:
        from skills.file_forge import generate_invoice_pdf_async
        file_path = await generate_invoice_pdf_async(client_name, amount, service_description)
        
        with open(file_path, 'rb') as doc:
            await context.bot.send_document(
                chat_id=chat_id, 
                document=doc, 
                caption=f"Счет для {client_name} на сумму {amount}",
                read_timeout=90,
                write_timeout=90
            )
        await status_msg.delete()
    except Exception as e:
        logger.exception("Error generating invoice")
        await status_msg.edit_text(f"❌ Ошибка генерации счета: {str(e)}")

async def handle_recon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ensure_chat_id_saved(chat_id)
    status_msg = await context.bot.send_message(chat_id, "🔍 Собираю Recon Brief. Пожалуйста, подождите...")
    
    try:
        from skills.recon_dump import fetch_news_async, generate_brief_async
        raw_data = await fetch_news_async()
        brief = await generate_brief_async(raw_data)
        await safe_send_message(context, chat_id, brief)
        await status_msg.delete()
    except Exception as e:
        logger.exception("Error in /recon")
        await status_msg.edit_text(f"❌ Ошибка генерации брифа: {str(e)}")

async def handle_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ensure_chat_id_saved(chat_id)
    args = context.args
    
    if not args:
        await update.message.reply_text("Использование:\n/schedule 09:00 - включить на заданное время\n/schedule off - выключить\n/schedule status - статус")
        return
        
    cmd = args[0].lower()
    from skills.recon_dump import update_schedule, get_current_schedule
    
    if cmd == "status":
        cfg = get_current_schedule()
        enabled = "ВКЛЮЧЕНА" if cfg.get("is_enabled") else "ВЫКЛЮЧЕНА"
        t = cfg.get("schedule_time", "09:00")
        tz = cfg.get("timezone", "Asia/Almaty")
        await update.message.reply_text(f"Статус рассылки: {enabled}\nВремя: {t} ({tz})")
    elif cmd == "off":
        cfg = get_current_schedule()
        update_schedule(cfg.get("schedule_time", "09:00"), False)
        await update.message.reply_text("✅ Автоматическая рассылка утреннего брифа отключена.")
    else:
        import re
        if re.match(r"^\d{2}:\d{2}$", cmd):
            success, msg = update_schedule(cmd, True)
            if success:
                await update.message.reply_text(f"✅ Расписание установлено на {cmd}. Бриф будет приходить каждый день.")
            else:
                await update.message.reply_text(f"❌ Ошибка установки расписания: {msg}")
        else:
            await update.message.reply_text("Неверный формат времени. Используйте ЧЧ:ММ (например 09:00)")

async def handle_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ensure_chat_id_saved(chat_id)
    args = context.args
    
    if not args:
        await update.message.reply_text("Использование:\n/topic Крипта, Биткоин, Web3")
        return
        
    topic = " ".join(args)
    from skills.recon_dump import load_config, save_config
    config = load_config()
    config["focus_topic"] = topic
    save_config(config)
    
    await update.message.reply_text(f"Фокус обновлен: {topic}")

async def start_bot():
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("Telegram bot token not configured in .env, bot will not start.")
        return
        
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).read_timeout(90).write_timeout(90).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("invoice", handle_invoice))
    app.add_handler(CommandHandler("recon", handle_recon))
    app.add_handler(CommandHandler("schedule", handle_schedule))
    app.add_handler(CommandHandler("topic", handle_topic))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unified_message_handler))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    
    print("Starting Telegram bot polling...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

def send_photo_alert(image_bytes: bytes, caption: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        response = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
            files={"photo": ("alert.jpg", image_bytes, "image/jpeg")},
            timeout=15,
        )
        response.raise_for_status()
        return True
    except Exception as exc:
        print(f"[TELEGRAM ALERT ERROR] {exc}")
        return False
