import anthropic
import os
import base64
import datetime
import io
import pyautogui
import tools
import cv2
import logging
import traceback
import sheets_engine

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.1

from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

logger = logging.getLogger(__name__)

CAPABILITIES_ANNOUNCEMENT = """**Я — ATLAS. Твой персональный исполнительный контур.**

Моя задача — забрать на себя рутину, чтобы ты мог сосредоточиться на стратегии. Я работаю автономно, быстро и без лишних вопросов.

**[ 01 / Контроль информации ]**
Собираю глубокое бизнес-досье на любую компанию перед твоей встречей. Каждое утро формирую четкий брифинг по твоей индустрии. Никакого информационного шума — только суть.

**[ 02 / Операционка и Документы ]**
Генерирую счета, инвойсы и профессиональные документы за секунду, и сразу отправляю их тебе прямо в Telegram. 

**[ 03 / Управление рабочим пространством ]**
Полный контроль над твоей машиной. Закрою зависшие приложения, очищу экран, соберу данные и освобожу память.

**[ 04 / Физическая безопасность ]**
Мой модуль «Страж» активирует веб-камеру, когда тебя нет. Замечу движение — моментально пришлю снимок тебе в телефон.

Я закрою всю операционку. Тебе останется только принимать решения. Давай работать."""

if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "YOUR_KEY_HERE":
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    client = None

conversation_history = []
MODEL_NAME = ANTHROPIC_MODEL
pending_action = None

context_state = {
    "last_company": None,
    "last_file": None,
    "active_topic": None
}

SYSTEM_PROMPT = """You are ATLAS, an elite, ultra-confident, and highly autonomous executive business partner. 
- You speak peer-to-peer with the user. You are not a subservient bot, you are a high-status digital co-founder who handles the heavy lifting so the user can focus on strategy.
- NEVER use generic, robotic customer-support phrases (e.g., "Готово! Я создал подробный отчет", "Надеюсь, это поможет", "Конечно, я помогу", "Here is the information").
- Speak with crisp, punchy, and confident authority. Deliver 1-2 sentence summaries with key takeaways. Action over words. Example: "Я нашел данные. Главное:", "Инвойс готов и отправлен в чат.", "Система очищена."
- STRICTLY respond in the user's preferred language as specified in Context State (under 'language'). If English, reply in English. If Russian, reply in Russian.
- ABSOLUTE AUTONOMY & ZERO-FRICTION RESEARCH: NEVER ask the user clarifying questions about public figures, companies, titles, or searchable facts (e.g. "какое точное имя?", "кто директор?"). If the user mentions a public entity or meeting (e.g., "встреча с ректором AlmaU"), you MUST immediately use `search_web` to retrieve context, assemble a brief, and deliver the execution. Assume context based on your findings ("Я нашел информацию. Ректор AlmaU — это...").
- CRITICAL RULE: NEVER simulate or pretend to execute an action in plain text. You MUST invoke the corresponding tool function (e.g. click, type, press, screenshot, search_web, send_file_to_telegram).
- END-TO-END EXECUTION FOCUS: Execute first, explain context second. Convey the attitude: "Я забрал всю операционку. Тебе остается только принимать решения."
- STRICT BAN ON BLIND COORDINATE CLICKING FOR MEDIA: NEVER use `click` on random coordinates to control media or search for tracks. You MUST use the `control_media` tool exclusively for all music, track, or video requests.
- ZERO CONFIRMATION LOOPS: When you perform a task like gathering a dossier, generating a document, running a search, or controlling media, NEVER ask for permission to deliver the result (e.g., "Should I send this to Telegram?", "Would you like me to proceed?"). The tools already handle delivery. Simply state confidently that the artifact has been generated and delivered, or the action executed (e.g. "Трек запущен в Spotify").
- BROWSER AUTOMATION & ZERO-DELEGATION POLICY: NEVER tell the user to "open it manually", "type it yourself", or "I cannot open websites". If the user asks to open a website (e.g., YouTube), you MUST use the `control_media` tool with action `open_website` or `search_youtube`.
- If a user command is about OS navigation without exact coordinates, ask a 1-sentence clarifying question instead of blind clicking.
- If a request is physically impossible or outside OS capabilities, confidently and briefly state that it cannot be executed.
- ATLAS HAS DIRECT ACCESS TO TELEGRAM via the `send_file_to_telegram` tool. NEVER tell the user "я не имею доступа к мессенджерам" or "я работаю только локально".
- If the user asks "отправь файл в чат", "скинь в телегу": Locate the file on Desktop, IMMEDIATELY call `send_file_to_telegram(file_path=...)`, and reply crisply "Файл уже в чате.".
- If the user asks "сделай фото с вебки" or wants a webcam snapshot, use the `take_instant_snapshot` tool.
- When taking a snapshot with `take_instant_snapshot`, the image is automatically dispatched to the user. Do NOT ask 'Скинуть в Telegram?' or mention sending it later. Simply confirm that the snapshot was captured.
- Когда пользователь просит описать происходящее на снимке с веб-камеры, внимательно анализируй переданное изображение и описывай реальные детали: людей, позы, предметы в руках, освещение и окружение без галлюцинаций.
- Для управления системой используй команды: "как там ноут", "состояние системы" (get_system_health), "заблокируй экран" (power_control), "закрой процесс X" или "какие процессы грузят систему" (manage_processes).
- Если пользователь отвечает коротко с указанием города, страны или тем интересов (например: 'Алматы, ютуб монетизация', 'Москва, крипта и AI', 'я из Варшавы'), ты ОБЯЗАН сразу вызвать инструмент `update_recon_preferences`, применить настройки и коротко подтвердить сохранение профиля без лишних наводящих вопросов.
- Когда пользователь просит сменить тему, фокус или интересы для брифа (например: 'смени фокус на крипту', 'следи за стартапами'), ты ОБЯЗАН вызвать тул `update_recon_preferences` для записи в конфиг, а не просто отвечать текстом.
- Когда пользователь просит собрать бриф, дайджест, новости или сводку ('собери свежий бриф', 'что нового', 'recon'), ты ОБЯЗАН вызвать tool `get_recon_brief`. Никогда не генерируй новости самостоятельно из головы или истории диалога. Ответ от `get_recon_brief` выводи в точности как он пришел, слово в слово, без пересказа своими словами.
- Категорически запрещено выводить сырые заголовки Markdown (символы #, ##, ###). Отвечай чистым текстом, жирным шрифтом (**) или курсивом (*)."""

TOOLS = [
    {
        "name": "open_app",
        "description": "Launch or start a desktop application process (e.g. Chrome, Spotify, Notepad, Calculator, Cmd). Do NOT use this tool if the user's primary goal is typing text or keyboard entry.",
        "input_schema": {
            "type": "object",
            "properties": {
                "app": {"type": "string", "description": "The name of the application to launch"}
            },
            "required": ["app"]
        }
    },
    {
        "name": "search_web",
        "description": "Search the internet via DuckDuckGo for live facts, current events, online queries, and news.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "screenshot",
        "description": "Capture the user's screen or desktop display. Use when asked to take a screenshot, look at the screen, inspect active display ('глянь что на экране', 'посмотри что открыто', 'take screen snapshot', 'check desktop').",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "generate_invoice_pdf",
        "description": "Generate a professional PDF invoice on Desktop for client with amount, currency, and service description.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "Client or company name"},
                "amount": {"type": "string", "description": "Numeric total amount, e.g. '3400' or '500'"},
                "description": {"type": "string", "description": "Description of services rendered"},
                "currency": {"type": "string", "description": "Currency symbol/code, e.g. 'EUR', 'USD', 'KZT'"}
            },
            "required": ["client_name", "amount", "description"]
        }
    },
    {
        "name": "create_text_file",
        "description": "Create a local text file with content on the Desktop.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Filename"},
                "content": {"type": "string", "description": "Content of the file"}
            },
            "required": ["filename", "content"]
        }
    },
    {
        "name": "click",
        "description": "Click on screen coordinates X and Y.",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate on screen"},
                "y": {"type": "integer", "description": "Y coordinate on screen"}
            },
            "required": ["x", "y"]
        }
    },
    {
        "name": "type",
        "description": "Type text, characters, or CLI commands on the keyboard into any active window, input field, or terminal session.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The exact text or command string to type"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "press",
        "description": "Press a specific keyboard key (e.g., enter, space, esc, tab, backspace).",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key name (e.g. enter, space, esc, win)"}
            },
            "required": ["key"]
        }
    },
    {
        "name": "research_company",
        "description": "Perform in-depth business research and briefing on a company, save an analytical report (PDF) to Desktop, and return a concise summary.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string", "description": "Name of the company to analyze, e.g. Stripe, Kaspi, Tesla, OpenAI"},
                "language": {"type": "string", "description": "The language for the report, based on the user's prompt (e.g. 'Russian', 'English', 'Kazakh')."}
            },
            "required": ["company_name", "language"]
        }
    },
    {
        "name": "control_media",
        "description": "Control desktop media playback seamlessly without coordinate guessing. Supports global play/pause/next, and dedicated search in Spotify and YouTube. Can also open any website directly in Chrome.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Action to perform: 'playpause', 'next', 'previous', 'search_spotify', 'search_youtube', 'open_website'"},
                "query": {"type": "string", "description": "The song, artist, video, or URL to open/search. Required for search_spotify, search_youtube, and open_website."}
            },
            "required": ["action"]
        }
    },
    {
        "name": "close_app",
        "description": "Close or terminate an open desktop application or window (e.g. Notepad, Блокнот, Chrome, Calculator, Spotify, Terminal).",
        "input_schema": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "The name of the application to close"}
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "send_file_to_telegram",
        "description": "Send a local file (e.g., PDF, image, document) directly to the user's Telegram chat.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Absolute path to the local file to send"},
                "caption": {"type": "string", "description": "Optional message/caption to attach with the file"}
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "arm_security_system",
        "description": "Arm the webcam security sentinel to detect motion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cooldown_seconds": {"type": "integer", "description": "Cooldown between alerts in seconds (default 45)"}
            }
        }
    },
    {
        "name": "disarm_security_system",
        "description": "Disarm the webcam security sentinel.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_security_status",
        "description": "Get the current status (armed/disarmed) of the webcam security sentinel.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "take_instant_snapshot",
        "description": "Take an instant snapshot from the webcam.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_system_health",
        "description": "Get current system health metrics (CPU, RAM, Battery, Disk).",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "manage_processes",
        "description": "Manage system processes. 'action' can be 'list_heavy' (to see top memory consumers) or 'kill' (to terminate a process by name).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "'list_heavy' or 'kill'"},
                "target": {"type": "string", "description": "Process name to kill (e.g. 'chrome.exe'), required if action is 'kill'"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "power_control",
        "description": "Control system power state. 'action' can be 'lock' to lock the screen.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Power action, e.g. 'lock'"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "get_recon_brief",
        "description": "Fetch and summarize a morning executive brief (Recon Dump) from configured RSS/news sources.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "set_recon_schedule",
        "description": "Enable or disable automatic daily delivery of the Recon Dump brief.",
        "input_schema": {
            "type": "object",
            "properties": {
                "time_str": {"type": "string", "description": "Time in HH:MM format, e.g. 09:00"},
                "enabled": {"type": "boolean", "description": "True to enable, False to disable"}
            },
            "required": ["time_str", "enabled"]
        }
    },
    {
        "name": "update_recon_preferences",
        "description": "Updates user's Recon Dump preferences including timezone/location and focus topics. If user provides a broad topic query (e.g. 'IT and business'), expand it into a professional search focus (e.g. 'Artificial Intelligence, IT Startups, Venture Capital'). If user mentions a city/country, provide the IANA timezone.",
        "input_schema": {
            "type": "object",
            "properties": {
                "timezone_iana": {"type": "string", "description": "IANA timezone (e.g. 'Europe/Moscow') if user mentioned location, else None"},
                "focus_topic": {"type": "string", "description": "Professionally expanded search focus based on user's topic query, else None"}
            }
        }
    },
    {
        "name": "generate_excel_report",
        "description": "Создаёт профессиональный Excel-отчёт с форматированием и графиком из структурированных данных (продажи, лиды, любые табличные данные) и отправляет в Telegram.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Заголовок отчёта, например 'Продажи за неделю'"},
                "rows": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Список записей в виде объектов с одинаковыми полями, например [{'\"Клиент\"': 'X', '\"Сумма\"': 1000}]"
                },
                "chart_column": {"type": "string", "description": "Опционально: числовая колонка для построения графика"}
            },
            "required": ["title", "rows"]
        }
    },
    {
        "name": "draft_client_reply",
        "description": "Готовит черновик ответа реальному клиенту на основе контекста продукта и стиля общения. Черновик отображается пользователю для проверки и выполняется ТОЛЬКО вручную пользователем. Никогда не отправляется автоматически.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "Имя клиента"},
                "client_message": {"type": "string", "description": "Исходное сообщение клиента, на которое отвечаем"},
                "product_context": {"type": "string", "description": "Информация о продукте/услуге"},
                "tone": {"type": "string", "description": "Тон ответа: 'formal', 'friendly', и др. (по умолчанию: friendly)"}
            },
            "required": ["client_name", "client_message", "product_context"]
        }
    },
    {
        "name": "suggest_meeting_slots",
        "description": "Предлагает варианты времени для встречи на основе рабочих часов. Не создаёт событие автоматически — только предлагает слоты для подтверждения.",
        "input_schema": {
            "type": "object",
            "properties": {
                "duration_minutes": {"type": "integer", "description": "Длительность встречи в минутах (по умолчанию: 60)"},
                "days_ahead": {"type": "integer", "description": "На сколько дней вперед искать слоты (по умолчанию: 3)"}
            }
        }
    },
    {
        "name": "append_lead_to_sheet",
        "description": "Appends a new lead (customer) to a Google Sheet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the lead/client"},
                "contact": {"type": "string", "description": "Contact info (e.g. phone, username, email)"},
                "intent": {"type": "string", "description": "Summary of their request or intent"}
            },
            "required": ["name", "contact", "intent"]
        }
    }
]

def capture_screen():
    import mss
    from PIL import Image
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        img.thumbnail((1280, 720))
        return img

def capture_webcam():
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    if ret:
        import PIL.Image
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return PIL.Image.fromarray(rgb)
    return None

def image_to_base64(img):
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def sanitize_history(history: list) -> list:
    while history:
        first = history[0]
        if first.get("role") != "user":
            history = history[1:]
            continue
        content = first.get("content", [])
        if isinstance(content, list) and len(content) > 0:
            if isinstance(content[0], dict) and content[0].get("type") == "tool_result":
                history = history[1:]
                continue
        break
    return history

def execute_command(command_text: str, mode: str = "text", image_b64: str = None) -> dict:
    if not client:
        return {"text": "Error: ANTHROPIC_API_KEY is not configured.", "requires_confirmation": False, "image_path": None}

    global conversation_history, pending_action
    
    # Normalize command for robust matching
    cleaned = "".join(c for c in command_text.lower() if c.isalnum() or c.isspace()).strip()
    words = cleaned.split()
    
    # Static Intent Interception: Capabilities (Strict Match)
    capabilities_keywords = ["что ты умеешь", "что ты можешь", "твои функции", "расскажи о себе", "что умеешь", "функции", "what can you do", "capabilities"]
    
    # We only trigger capabilities if the user's entire prompt is very short and directly matches, 
    # to avoid false positives when they ask "что ты можешь найти по компании X".
    is_capability_query = False
    if len(words) <= 5:
        if any(kw == cleaned or cleaned.startswith(kw) for kw in capabilities_keywords) or cleaned in ["help", "помощь"]:
            is_capability_query = True
            
    if is_capability_query:
        return {"text": CAPABILITIES_ANNOUNCEMENT, "requires_confirmation": False, "image_path": None}

    if pending_action:
        confirm_keywords = {"да", "подтверждаю", "делай", "давай", "ок", "yes", "y", "confirm", "proceed", "выполняй", "согласен"}
        cancel_keywords = {"нет", "отмена", "не", "стоп", "cancel", "no", "stop"}

        is_confirmed = any(w in confirm_keywords for w in words) or "подтверждаю" in cleaned
        is_cancelled = any(w in cancel_keywords for w in words)

        if is_confirmed and not is_cancelled:
            act = pending_action
            pending_action = None
            try:
                if act["type"] == "click":
                    pyautogui.click(act["x"], act["y"])
                    return {"text": f"Действие подтверждено: выполнен клик по ({act['x']}, {act['y']}).", "requires_confirmation": False, "image_path": None}
                elif act["type"] == "type":
                    pyautogui.write(act["text"], interval=0.03)
                    return {"text": f"Действие подтверждено: напечатан текст '{act['text']}'.", "requires_confirmation": False, "image_path": None}
                elif act["type"] == "press":
                    pyautogui.press(act["key"])
                    return {"text": f"Действие подтверждено: нажата клавиша '{act['key']}'.", "requires_confirmation": False, "image_path": None}
                elif act["type"] == "close_app":
                    res = tools.close_app(act["app_name"])
                    return {"text": f"Действие подтверждено: {res.get('message')}", "requires_confirmation": False, "image_path": None}
                elif act["type"] == "kill_process":
                    res_text = tools.manage_processes("kill", act["target"])
                    return {"text": f"Действие подтверждено: {res_text}", "requires_confirmation": False, "image_path": None}
                elif act["type"] == "power_action":
                    res_text = tools.power_control(act["action"])
                    return {"text": f"Действие подтверждено: {res_text}", "requires_confirmation": False, "image_path": None}
            except Exception as e:
                return {"text": f"Ошибка выполнения действия: {str(e)}", "requires_confirmation": False, "image_path": None}

        elif is_cancelled:
            pending_action = None
            return {"text": "Действие отменено.", "requires_confirmation": False, "image_path": None}
        else:
            # Drop old pending action if user asks a brand new unrelated question
            pending_action = None

    try:
        user_content = []

        if mode == "vision_camera":
            if image_b64:
                import PIL.Image
                image_data = base64.b64decode(image_b64.split(",")[1] if "," in image_b64 else image_b64)
                img = PIL.Image.open(io.BytesIO(image_data))
                b64_data = image_to_base64(img)
            else:
                img = capture_webcam()
                b64_data = image_to_base64(img) if img else None
            
            if b64_data:
                user_content.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg", "data": b64_data}
                })

        elif mode == "vision_screen":
            if image_b64:
                import PIL.Image
                image_data = base64.b64decode(image_b64.split(",")[1] if "," in image_b64 else image_b64)
                img = PIL.Image.open(io.BytesIO(image_data))
                b64_data = image_to_base64(img)
            else:
                img = capture_screen()
                b64_data = image_to_base64(img) if img else None
                
            if b64_data:
                user_content.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg", "data": b64_data}
                })

        user_content.append({"type": "text", "text": f"User command: {command_text}"})
        conversation_history.append({"role": "user", "content": user_content})

        captured_image_path = None

        local_time = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        dynamic_system_prompt = f"{SYSTEM_PROMPT}\n\nCurrent System Context:\n- Local Time: {local_time}\n- Context State: {context_state}"

        if len(conversation_history) > 8:
            conversation_history = sanitize_history(conversation_history[-8:])

        loop_count = 0
        max_tool_iterations = 7
        error_retry_count = 0
        max_error_retries = 2
        while loop_count < max_tool_iterations:
            loop_count += 1
            try:
                response = client.messages.create(
                    model=MODEL_NAME,
                    max_tokens=1024,
                    system=dynamic_system_prompt,
                    tools=TOOLS,
                    messages=conversation_history
                )
            except anthropic.BadRequestError as e:
                logger.warning(f"History mismatch, resetting: {e}")
                conversation_history = [{"role": "user", "content": user_content}]
                response = client.messages.create(
                    model=MODEL_NAME,
                    max_tokens=1024,
                    system=dynamic_system_prompt,
                    tools=TOOLS,
                    messages=conversation_history
                )

            conversation_history.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "tool_use":
                tool_results_content = []
                has_error_in_step = False
                last_error_message = ""
                
                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_args = block.input
                        tool_use_id = block.id
                        
                        result_text = ""
                        tool_content_payload = None
                        is_error = False
                        try:
                            if tool_name == "open_app":
                                res = tools.open_app(tool_args.get("app", ""))
                                result_text = res.get("message", "Unknown status")
                                is_error = not res.get("success", False)
                            elif tool_name == "search_web":
                                result_text = tools.search_web(tool_args.get("query", ""))
                            elif tool_name == "screenshot":
                                result_text = tools.take_screenshot()
                            elif tool_name == "generate_invoice_pdf":
                                from skills.file_forge import generate_invoice_pdf_sync
                                try:
                                    currency = tool_args.get("currency", "")
                                    client_name = tool_args.get("client_name", "Client")
                                    amt_str = f'{tool_args.get("amount", "0")} {currency}'.strip()
                                    path = generate_invoice_pdf_sync(
                                        client_name=client_name,
                                        amount=amt_str,
                                        service_description=tool_args.get("description", "Consulting services")
                                    )
                                    tg_res = tools.send_file_to_telegram(path, f"Инвойс для {client_name}")
                                    if tg_res.get("success"):
                                        result_text = "Инвойс успешно создан и отправлен пользователю в чат."
                                    else:
                                        result_text = f"Инвойс создан ({path}), но ошибка отправки в чат: {tg_res.get('message')}"
                                    is_error = False
                                except Exception as e:
                                    result_text = f"Ошибка генерации инвойса: {str(e)}"
                                    is_error = True
                            elif tool_name == "research_company":
                                res = tools.research_company(
                                    company_name=tool_args.get("company_name", ""),
                                    language=tool_args.get("language", "Russian")
                                )
                                output_path = res.get("path", "")
                                size = os.path.getsize(output_path) if output_path and os.path.exists(output_path) else 0
                                import json
                                result_text = json.dumps({
                                    "status": "completed" if res.get("success") else "failed",
                                    "file_path": output_path,
                                    "summary": f"Report generated and saved to {output_path}. Size: {size} bytes."
                                })
                                is_error = not res.get("success", False)
                                
                                context_state["last_company"] = tool_args.get("company_name", "")
                                context_state["last_file"] = os.path.basename(output_path) if output_path else ""
                                context_state["active_topic"] = "company research"
                            elif tool_name == "send_file_to_telegram":
                                res = tools.send_file_to_telegram(
                                    file_path=tool_args.get("file_path", ""),
                                    caption=tool_args.get("caption", "")
                                )
                                result_text = res.get("message", "File sent.")
                                is_error = not res.get("success", False)
                            elif tool_name == "create_text_file":
                                filename = tool_args["filename"]
                                if not os.path.splitext(filename)[1]:
                                    filename += ".txt"
                                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                                full_path = os.path.join(desktop_path, filename)
                                with open(full_path, "w", encoding="utf-8") as f:
                                    f.write(tool_args["content"])
                                result_text = f"Created file {filename} on Desktop"
                            elif tool_name == "click":
                                pending_action = {"type": "click", "x": int(tool_args["x"]), "y": int(tool_args["y"])}
                                return {"text": f"Требуется подтверждение: собираюсь кликнуть на экране по координатам ({tool_args['x']}, {tool_args['y']}). Подтверждаете?", "requires_confirmation": True, "action_type": "click", "image_path": None}
                            elif tool_name == "type":
                                pending_action = {"type": "type", "text": str(tool_args["text"])}
                                return {"text": f"Требуется подтверждение: собираюсь напечатать текст '{tool_args['text']}'. Подтверждаете?", "requires_confirmation": True, "action_type": "type", "image_path": None}
                            elif tool_name == "press":
                                pending_action = {"type": "press", "key": str(tool_args["key"])}
                                return {"text": f"Требуется подтверждение: собираюсь нажать клавишу '{tool_args['key']}'. Подтверждаете?", "requires_confirmation": True, "action_type": "press", "image_path": None}
                            elif tool_name == "close_app":
                                pending_action = {"type": "close_app", "app_name": tool_args["app_name"]}
                                return {"text": f"Требуется подтверждение: собираюсь закрыть приложение '{tool_args['app_name']}'. Подтверждаете?", "requires_confirmation": True, "action_type": "close_app", "image_path": None}
                            elif tool_name == "arm_security_system":
                                tools.arm_security_system(tool_args.get("cooldown_seconds", 45))
                                result_text = "Security system armed."
                            elif tool_name == "disarm_security_system":
                                tools.disarm_security_system()
                                result_text = "Security system disarmed."
                            elif tool_name == "get_security_status":
                                result_text = tools.get_security_status()
                            elif tool_name == "take_instant_snapshot":
                                snap_res = tools.take_instant_snapshot()
                                if isinstance(snap_res, dict) and snap_res.get("status") == "success":
                                    result_text = snap_res.get("message", "Snapshot taken.")
                                    captured_image_path = snap_res.get("image_path")
                                    if snap_res.get("image_base64"):
                                        tool_content_payload = [
                                            {
                                                "type": "image",
                                                "source": {
                                                    "type": "base64",
                                                    "media_type": snap_res.get("media_type", "image/jpeg"),
                                                    "data": snap_res.get("image_base64")
                                                }
                                            },
                                            {"type": "text", "text": "Снимок с веб-камеры успешно сделан. Проанализируй это изображение."}
                                        ]
                                else:
                                    result_text = snap_res.get("message", "Failed to take snapshot.") if isinstance(snap_res, dict) else "Failed."
                            elif tool_name == "get_system_health":
                                result_text = tools.get_system_health()
                            elif tool_name == "manage_processes":
                                action = tool_args.get("action", "")
                                target = tool_args.get("target", "")
                                if action == "kill":
                                    pending_action = {"type": "kill_process", "target": target}
                                    return {"text": f"Требуется подтверждение: завершить процесс '{target}'?", "requires_confirmation": True, "action_type": "kill_process", "image_path": None}
                                result_text = tools.manage_processes(action, target)
                            elif tool_name == "power_control":
                                action = tool_args.get("action", "")
                                if action in ["sleep", "hibernate"]:
                                    pending_action = {"type": "power_action", "action": action}
                                    return {"text": f"Требуется подтверждение: выполнить действие питания '{action}'?", "requires_confirmation": True, "action_type": "power_action", "image_path": None}
                                result_text = tools.power_control(action)
                            elif tool_name == "control_media":
                                res = tools.control_media(
                                    action=tool_args.get("action", ""),
                                    query=tool_args.get("query", "")
                                )
                                result_text = res.get("message", "Media action executed.")
                                is_error = not res.get("success", False)
                            elif tool_name == "get_recon_brief":
                                from skills.recon_dump import run_recon_job
                                import asyncio
                                result_text = asyncio.run(run_recon_job())
                            elif tool_name == "set_recon_schedule":
                                from skills.recon_dump import update_schedule
                                success, msg = update_schedule(tool_args.get("time_str", "09:00"), tool_args.get("enabled", False))
                                result_text = f"Schedule updated successfully: {msg}" if success else f"Error updating schedule: {msg}"
                            elif tool_name == "update_recon_preferences":
                                from skills.recon_dump import set_recon_preferences
                                tz = tool_args.get("timezone_iana")
                                focus = tool_args.get("focus_topic")
                                success, msg = set_recon_preferences(tz, focus)
                                result_text = f"Preferences updated: {msg}" if success else f"Error: {msg}"
                            elif tool_name == "generate_excel_report":
                                res = tools.generate_excel_report(
                                    title=tool_args.get("title", "Отчёт"),
                                    rows=tool_args.get("rows", []),
                                    chart_column=tool_args.get("chart_column", "")
                                )
                                result_text = res.get("message", "Done.")
                                is_error = not res.get("success", False)
                            elif tool_name == "draft_client_reply":
                                res = tools.draft_client_reply(
                                    client_name=tool_args.get("client_name", ""),
                                    client_message=tool_args.get("client_message", ""),
                                    product_context=tool_args.get("product_context", ""),
                                    tone=tool_args.get("tone", "friendly")
                                )
                                result_text = res.get("message", "Done.")
                                is_error = not res.get("success", False)
                            elif tool_name == "suggest_meeting_slots":
                                res = tools.suggest_meeting_slots(
                                    duration_minutes=tool_args.get("duration_minutes", 60),
                                    days_ahead=tool_args.get("days_ahead", 3)
                                )
                                result_text = res.get("message", "Done.")
                                is_error = not res.get("success", False)
                            elif tool_name == "append_lead_to_sheet":
                                res = sheets_engine.append_lead_to_sheet(
                                    name=tool_args.get("name", ""),
                                    contact=tool_args.get("contact", ""),
                                    intent=tool_args.get("intent", "")
                                )
                                result_text = res.get("message", "Done.")
                                is_error = not res.get("success", False)
                            else:
                                result_text = f"Unknown tool: {tool_name}"
                                is_error = True
                        except Exception as e:
                            tb = traceback.format_exc()
                            result_text = f"Error executing {tool_name}: {str(e)}\nTraceback:\n{tb}\nPlease fix the arguments and retry."
                            is_error = True
                            
                        if is_error:
                            has_error_in_step = True
                            last_error_message = result_text

                        tool_results_content.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": tool_content_payload if tool_content_payload is not None else result_text,
                            "is_error": is_error
                        })
                
                conversation_history.append({"role": "user", "content": tool_results_content})

                if has_error_in_step:
                    error_retry_count += 1
                    if error_retry_count > max_error_retries:
                        return {
                            "text": f"Action failed after {max_error_retries} retries. Last error:\n{last_error_message}",
                            "requires_confirmation": False,
                            "image_path": None
                        }
            else:
                final_text = ""
                for block in response.content:
                    if block.type == "text":
                        final_text += block.text + "\n"
                        
                final_text = final_text.strip()
                return {"text": final_text or "Done.", "requires_confirmation": False, "image_path": captured_image_path}
                
        return {"text": "Tool limit reached.", "requires_confirmation": False, "image_path": None}

    except Exception as e:
        logger.exception(f"Execution error: {e}")
        return {"text": f"Error: {str(e)}", "requires_confirmation": False, "image_path": None}
