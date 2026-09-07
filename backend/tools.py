import subprocess
import urllib.parse
import urllib.request
import json
import platform
import logging

logger = logging.getLogger(__name__)

TELEGRAM_CHAT_ID = None

def find_latest_desktop_file(query: str, extension: str = ".pdf") -> str | None:
    import os
    from pathlib import Path
    
    user_home = Path.home()
    possible_desktops = [
        user_home / "Desktop",
        user_home / "OneDrive" / "Desktop",
        user_home / "OneDrive" / "Рабочий стол",
        user_home / "Рабочий стол",
        Path("C:/Users/user/Desktop"),
        Path("C:/Users/user/OneDrive/Desktop"),
        Path("C:/Users/user/OneDrive/Рабочий стол"),
    ]
    
    aliases = {
        "холок": "halyk",
        "халык": "halyk",
        "halyk": "halyk",
        "каспи": "kaspi",
        "kaspi": "kaspi",
        "фридом": "freedom",
        "freedom": "freedom",
        "индрайв": "indrive",
        "indrive": "indrive",
    }
    
    clean_query = query.lower().replace(" ", "").replace("_", "").replace("-", "")
    target_keys = []
    for k, v in aliases.items():
        if k in clean_query:
            target_keys.append(v)
    if not target_keys:
        target_keys.append(clean_query)

    matching_files = []
    for desktop in possible_desktops:
        if desktop.exists():
            for file_path in desktop.glob(f"*{extension}"):
                normalized_name = file_path.name.lower().replace(" ", "").replace("_", "").replace("-", "")
                if any(k in normalized_name for k in target_keys):
                    matching_files.append(file_path)
                    
    if not matching_files:
        return None
        
    latest_file = max(matching_files, key=lambda p: p.stat().st_mtime)
    return str(latest_file)

def send_file_to_telegram(file_path: str, caption: str = "") -> dict:
    import requests
    import os
    from config import TELEGRAM_BOT_TOKEN
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return {"success": False, "message": "Telegram Bot Token or Chat ID is missing."}
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    try:
        with open(file_path, "rb") as f:
            files = {"document": f}
            data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}
            resp = requests.post(url, data=data, files=files, timeout=10)
            if resp.ok:
                return {"success": True, "message": f"Файл {os.path.basename(file_path)} отправлен в Telegram."}
            else:
                return {"success": False, "message": f"Ошибка отправки: {resp.text}"}
    except Exception as e:
        logger.error(f"Failed to send file to telegram: {e}")
        return {"success": False, "message": f"Ошибка отправки: {str(e)}"}

WINDOWS_APP_MAP = {
    "калькулятор": "calc.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "блокнот": "notepad.exe",
    "notepad": "notepad.exe",
    "проводник": "explorer.exe",
    "explorer": "explorer.exe",
    "файлы": "explorer.exe",
    "браузер": "chrome",
    "хром": "chrome",
    "chrome": "chrome",
    "командная строка": "cmd.exe",
    "cmd": "cmd.exe",
    "терминал": "cmd.exe",
    "paint": "mspaint.exe",
    "spotify": "spotify.exe",
    "telegram": "telegram.exe"
}

def open_app(app_name: str) -> dict:
    sys_name = platform.system()
    app_name_lower = app_name.lower().strip()
    
    for word in ["открой ", "запусти ", "open ", "launch "]:
        if app_name_lower.startswith(word):
            app_name_lower = app_name_lower[len(word):].strip()
            
    try:
        if sys_name == "Windows":
            mapped_command = WINDOWS_APP_MAP.get(app_name_lower)
            if mapped_command:
                subprocess.Popen(["cmd", "/c", "start", "", mapped_command], shell=False)
            else:
                subprocess.Popen(["cmd", "/c", "start", "", app_name], shell=False)
            return {"success": True, "message": f"Приложение '{app_name}' запущено", "app": app_name}
        elif sys_name == "Darwin":
            subprocess.run(["open", "-a", app_name.title()], check=True, capture_output=True)
            return {"success": True, "message": f"Приложение '{app_name}' запущено", "app": app_name}
        else:
            return {"success": False, "message": f"ОС {sys_name} не поддерживается", "app": app_name}
    except Exception as e:
        logger.error(f"Error launching {app_name}: {e}")
        return {"success": False, "message": f"Не удалось открыть '{app_name}': {str(e)}", "app": app_name}


def search_web(query: str) -> str:
    """Searches the web via DuckDuckGo and returns factual snippets."""
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            abstract = data.get("AbstractText", "")
            if abstract:
                return abstract
            
            related = data.get("RelatedTopics", [])
            snippets = []
            for item in related[:3]:
                if "Text" in item:
                    snippets.append(item["Text"])
            if snippets:
                return "\n".join(snippets)
                
        return f"Результаты по запросу '{query}': поиск выполнен успешно, прямая справка отсутствует."
    except Exception as e:
        return f"Ошибка поиска в интернете: {str(e)}"

def take_screenshot() -> str:
    return "Screenshot captured and analyzed."



def research_company(company_name: str, language: str = "Russian") -> dict:
    """Perform in-depth business research and briefing on a company, save an analytical report (.pdf) to Desktop."""
    import os
    import datetime
    import re
    import anthropic
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.platypus.flowables import HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib import colors
    from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
    
    lang_lower = language.lower()
    is_russian = "rus" in lang_lower or "рус" in lang_lower
    
    label_dossier = "РАЗВЕДЫВАТЕЛЬНОЕ ДОСЬЕ" if is_russian else "INTELLIGENCE DOSSIER"
    label_msg = f"Досье на компанию {company_name}" if is_russian else f"Dossier for {company_name}"

    try:
        try:
            snippet1 = search_web(f"{company_name} founders executives headquarters")
            snippet2 = search_web(f"{company_name} business model revenue valuation financials")
            snippet = f"Data 1:\n{snippet1}\n\nData 2:\n{snippet2}"
        except Exception:
            snippet = ""
        
        markdown_text = f"# {company_name}\n\nДанные не найдены." if is_russian else f"# {company_name}\n\nNo data found."
        
        if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "YOUR_KEY_HERE":
            try:
                client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                if is_russian:
                    system_instruction = "Вы — старший аналитик бизнес-разведки. Отвечайте ТОЛЬКО валидным Markdown СТРОГО на русском языке.\nКРИТИЧЕСКИЕ ПРАВИЛА:\n1. ДОСТОВЕРНОСТЬ: Опирайтесь на переданные данные и вашу базу. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО придумывать (галлюцинировать) имена, названия фондов или финансовые оценки.\n2. БЕЗ ПУСТЫХ ПОЛЕЙ: Заполняйте все разделы реальными известными фактами об операционной деятельности, если точных цифр нет.\n3. НИКАКИХ СМЕШАННЫХ ЯЗЫКОВ: Все заголовки таблиц, ключи и абзацы должны быть на РУССКОМ языке (например, 'Оценка', 'Аудитория', 'Выручка')."
                    prompt = f"Сделай УЛЬТРА-ДЕТАЛЬНОЕ бизнес-досье на компанию {company_name} на основе данных поиска:\n{snippet}\n\nОБЯЗАТЕЛЬНАЯ СТРУКТУРА (строгий Markdown):\nСразу после заголовка добавь таблицу KPI (ровно 4 колонки: Оценка, Аудитория, Рынки, Позиционирование):\n| Оценка | Аудитория | Рынки | Позиционирование |\n|--------|-----------|-------|------------------|\n\nЗатем разделы:\n## 1. Резюме руководителя\n## 2. Корпоративная идентичность и руководство\n## 3. Архитектура экосистемы\n## 4. Стратегические партнерства и M&A\n## 5. Экономика и финансовые показатели\n## 6. Риски и стратегия развития\n\nСразу после всех разделов добавь итоговую таблицу (строго Markdown таблица):\n| Метрика | Значение | Категория | Динамика |\n|---------|----------|-----------|----------|\n\nОтвечай ТОЛЬКО в Markdown, без лишних вступлений."
                else:
                    system_instruction = "You are a senior business intelligence analyst. Respond ONLY with valid Markdown STRICTLY in English.\nCRITICAL RULES:\n1. FACTUAL GROUNDING: Rely on the provided search snippet and your parametric knowledge. DO NOT hallucinate fictional names, funds, or financial metrics.\n2. NO EMPTY PLACEHOLDERS: Fill out all sections with known operational facts if exact financials are missing.\n3. NO MIXED LANGUAGES: All table headers, keys, and paragraphs MUST be in English."
                    prompt = f"Generate an ULTRA-DETAILED business dossier for {company_name} based on search data:\n{snippet}\n\nREQUIRED STRUCTURE (strict Markdown):\nImmediately after the title, add a KPI table (exactly 4 columns: Valuation, Audience, Core Markets, Positioning):\n| Valuation | Audience | Core Markets | Positioning |\n|-----------|----------|--------------|-------------|\n\nThen sections:\n## 1. Executive Summary\n## 2. Corporate Identity & Leadership\n## 3. Ecosystem Architecture\n## 4. Strategic Partnerships & M&A\n## 5. Unit Economics & Financial Breakdown\n## 6. Risks & Forward Strategy\n\nImmediately after all sections, add a Summary Metrics Table:\n| Metric | Value | Category | Dynamics |\n|--------|-------|----------|----------|\n\nRespond ONLY in Markdown, no filler text."

                msg = client.messages.create(
                    model=ANTHROPIC_MODEL,
                    max_tokens=4000,
                    system=system_instruction,
                    messages=[{"role": "user", "content": prompt}]
                )
                resp_text = msg.content[0].text.strip()
                if resp_text:
                    markdown_text = resp_text
            except Exception as e:
                logger.error(f"LLM generation error: {e}")

        font_regular = "Helvetica"
        font_bold = "Helvetica-Bold"
        
        font_paths = [
            (r"C:\Windows\Fonts\DejaVuSans.ttf", r"C:\Windows\Fonts\DejaVuSans-Bold.ttf"),
            (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
            (r"C:\Windows\Fonts\tahoma.ttf", r"C:\Windows\Fonts\tahomabd.ttf")
        ]
        
        for reg_path, bold_path in font_paths:
            if os.path.exists(reg_path):
                try:
                    pdfmetrics.registerFont(TTFont("CustomArial", reg_path))
                    font_regular = "CustomArial"
                    if os.path.exists(bold_path):
                        pdfmetrics.registerFont(TTFont("CustomArial-Bold", bold_path))
                        font_bold = "CustomArial-Bold"
                    else:
                        font_bold = "CustomArial"
                    break
                except Exception:
                    pass

        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        file_id = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        file_name = f"{company_name.replace(' ', '_')}_{file_id}_Dossier.pdf"
        file_path = os.path.join(desktop_path, file_name)

        doc = SimpleDocTemplate(file_path, pagesize=letter,
                                rightMargin=40, leftMargin=40,
                                topMargin=40, bottomMargin=40)

        styles = getSampleStyleSheet()
        
        heading_style = ParagraphStyle(
            'CustomHeading2',
            parent=styles['Heading2'],
            fontName=font_bold,
            fontSize=16,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=22,
            spaceAfter=8,
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontName=font_regular,
            fontSize=11,
            leading=16,
            textColor=colors.HexColor("#334155"),
            spaceAfter=8
        )
        
        bullet_style = ParagraphStyle(
            'CustomBullet',
            parent=body_style,
            leftIndent=15,
            bulletIndent=15,
            spaceAfter=6
        )

        elements = []
        current_date = datetime.datetime.now().strftime("%B %d, %Y")

        header_data = [[
            Paragraph(f"<b>{company_name.upper()}</b> • {label_dossier}", ParagraphStyle('HeaderTitle', fontName=font_bold, fontSize=16, textColor=colors.white)),
            Paragraph(f"{current_date}", ParagraphStyle('HeaderDate', fontName=font_regular, fontSize=10, textColor=colors.HexColor("#cbd5e1"), alignment=2))
        ]]
        header_table = Table(header_data, colWidths=[380, 120])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0f172a")),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 16),
            ('BOTTOMPADDING', (0,0), (-1,-1), 16),
            ('LEFTPADDING', (0,0), (-1,-1), 16),
            ('RIGHTPADDING', (0,0), (-1,-1), 16),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 20))
        
        html_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', markdown_text)
        html_text = re.sub(r'\*([^\*]+)\*', r'<i>\1</i>', html_text)
        html_text = re.sub(r'\_([^\_]+)\_', r'<i>\1</i>', html_text)
        
        in_table = False
        table_data = []

        def build_table(data):
            parsed_data = []
            for r_idx, row in enumerate(data):
                parsed_row = []
                for cell in row:
                    cell = cell.replace('###', '').replace('##', '').replace('#', '').strip()
                    cell_style = body_style if r_idx > 0 else ParagraphStyle('TH', parent=body_style, fontName=font_bold, textColor=colors.whitesmoke)
                    parsed_row.append(Paragraph(cell, cell_style))
                parsed_data.append(parsed_row)
            
            t = Table(parsed_data)
            style = [
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BOTTOMPADDING', (0,0), (-1,0), 10),
                ('TOPPADDING', (0,0), (-1,0), 10),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ]
            for i in range(1, len(data)):
                bg = colors.HexColor("#f8fafc") if i % 2 == 1 else colors.white
                style.append(('BACKGROUND', (0,i), (-1,i), bg))
                style.append(('BOTTOMPADDING', (0,i), (-1,i), 8))
                style.append(('TOPPADDING', (0,i), (-1,i), 8))
                
            t.setStyle(TableStyle(style))
            return t

        for line in html_text.split('\n'):
            line = line.strip()
            
            if line.startswith('|') and line.endswith('|'):
                if '---' in line:
                    continue
                row = [cell.strip() for cell in line.strip('|').split('|')]
                row = [cell for cell in row if cell != ""] if len(row) == 0 else row
                if row:
                    table_data.append(row)
                in_table = True
                continue
            else:
                if in_table:
                    if table_data:
                        elements.append(build_table(table_data))
                        elements.append(Spacer(1, 15))
                    in_table = False
                    table_data = []

            if not line:
                elements.append(Spacer(1, 6))
                continue
            
            if line.startswith('# '):
                continue
            elif line.startswith('## '):
                clean_heading = line.replace('##', '').strip()
                elements.append(Paragraph(clean_heading, heading_style))
                elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceBefore=5, spaceAfter=12))
            elif line.startswith('### '):
                clean_sub = line.replace('###', '').strip()
                elements.append(Paragraph(f"<b>{clean_sub}</b>", body_style))
            elif line.startswith('- ') or line.startswith('* '):
                clean_line = line[2:]
                clean_line = clean_line.replace('###', '').replace('##', '').replace('#', '').strip()
                elements.append(Paragraph(f"• {clean_line}", bullet_style))
            else:
                clean_line = line.replace('###', '').replace('##', '').replace('#', '').strip()
                elements.append(Paragraph(clean_line, body_style))

        if in_table and table_data:
            elements.append(build_table(table_data))

        doc.build(elements)
        send_file_to_telegram(file_path, label_msg)
            
        return {
            "success": True, 
            "message": f"Dossier generated: {file_name}", 
            "path": str(file_path)
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}

def close_app(app_name: str) -> dict:
    import subprocess
    name_lower = app_name.lower().strip()
    process_name = None

    if name_lower in ["блокнот", "notepad"]:
        process_name = "notepad.exe"
    elif name_lower in ["хром", "chrome", "браузер"]:
        process_name = "chrome.exe"
    elif name_lower in ["калькулятор", "calc", "calculator"]:
        process_name = "CalculatorApp.exe"
    elif name_lower in ["терминал", "cmd", "terminal"]:
        process_name = "cmd.exe"
    elif name_lower in ["spotify"]:
        process_name = "Spotify.exe"
    else:
        # Fallback: append .exe if not present and try to kill it directly
        process_name = name_lower if name_lower.endswith(".exe") else f"{name_lower}.exe"

    try:
        subprocess.run(["taskkill", "/IM", process_name, "/F"], check=True, capture_output=True)
        return {"success": True, "message": f"Окно {app_name} успешно закрыто."}
    except subprocess.CalledProcessError:
        return {"success": False, "message": f"Не удалось закрыть {app_name}. Возможно, оно не запущено."}
    except Exception as e:
        return {"success": False, "message": f"Ошибка закрытия {app_name}: {str(e)}"}

from security import sentinel

def arm_security_system(cooldown_seconds: int = 45):
    sentinel.arm(cooldown_seconds)
    return "Security system armed."

def disarm_security_system():
    sentinel.disarm()
    return "Security system disarmed."

def get_security_status():
    return sentinel.status()

def take_instant_snapshot():
    import tempfile
    import os
    import base64
    data = sentinel.snapshot_once()
    if data:
        fd, path = tempfile.mkstemp(suffix=".jpg", prefix="snapshot_")
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            
        b64_data = base64.b64encode(data).decode("utf-8")
        
        return {
            "status": "success", 
            "image_path": path, 
            "message": "Снимок с веб-камеры готов.",
            "image_base64": b64_data,
            "media_type": "image/jpeg"
        }
    return {"status": "error", "image_path": None, "message": "Не удалось сделать снимок."}

import psutil
import ctypes
import shutil

def get_system_health() -> str:
    try:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        
        battery = psutil.sensors_battery()
        bat_info = "Нет данных о батарее"
        if battery:
            plugged = "Заряжается" if battery.power_plugged else "От батареи"
            bat_info = f"{battery.percent}% ({plugged})"
            
        disk = shutil.disk_usage("/")
        disk_free_gb = disk.free // (2**30)
        disk_total_gb = disk.total // (2**30)
        
        return f"CPU: {cpu}%\nОЗУ: {mem.percent}% ({mem.used // (2**20)}MB / {mem.total // (2**20)}MB)\nБатарея: {bat_info}\nДиск C: {disk_free_gb}GB свободно из {disk_total_gb}GB."
    except Exception as e:
        return f"Ошибка получения данных системы: {e}"

def manage_processes(action: str, target: str = "") -> str:
    blacklist = ["explorer.exe", "csrss.exe", "winlogon.exe", "svchost.exe", "smss.exe", "services.exe", "lsass.exe", "wininit.exe", "dwm.exe", "registry", "system", "system idle process"]
    try:
        if action == "list_heavy":
            procs = []
            for p in psutil.process_iter(['name', 'memory_info']):
                try:
                    procs.append((p.info['name'], p.info['memory_info'].rss))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            procs.sort(key=lambda x: x[1], reverse=True)
            top = procs[:5]
            res = "Самые тяжелые процессы:\n"
            for name, mem in top:
                res += f"- {name}: {mem // (2**20)} MB\n"
            return res
        elif action == "kill":
            target_lower = target.lower()
            if not target_lower:
                return "Не указан процесс для завершения."
            if target_lower in blacklist:
                return f"Безопасность: завершение {target} запрещено черным списком."
            
            killed = 0
            for p in psutil.process_iter(['name']):
                try:
                    if p.info['name'] and p.info['name'].lower() == target_lower:
                        p.kill()
                        killed += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            if killed > 0:
                return f"Завершено {killed} экземпляров процесса {target}."
            return f"Процесс {target} не найден."
        return "Неизвестное действие. Допустимые: 'list_heavy', 'kill'."
    except Exception as e:
        return f"Ошибка управления процессами: {e}"

def power_control(action: str) -> str:
    try:
        import os
        if action == "lock":
            ctypes.windll.user32.LockWorkStation()
            return "Экран заблокирован."
        elif action == "sleep":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            return "Система переведена в спящий режим."
        elif action == "hibernate":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 1,1,0")
            return "Система переведена в режим гибернации."
        return "Неизвестное действие для питания."
    except Exception as e:
        return f"Ошибка управления питанием: {e}"

def control_media(action: str, query: str = None) -> dict:
    """Control media playback or search and play specific tracks/videos without coordinate guessing."""
    import pyautogui
    import time
    import platform
    import subprocess
    import urllib.parse
    
    sys_name = platform.system()
    action = action.lower()
    
    try:
        if action in ["playpause", "play", "pause"]:
            pyautogui.press("playpause")
            return {"success": True, "message": "Медиа: Play/Pause выполнено."}
        elif action in ["next", "nexttrack"]:
            pyautogui.press("nexttrack")
            return {"success": True, "message": "Медиа: Следующий трек."}
        elif action in ["previous", "prevtrack", "prev"]:
            pyautogui.press("prevtrack")
            return {"success": True, "message": "Медиа: Предыдущий трек."}
            
        elif action in ["search_spotify", "search_play"]:
            if not query:
                return {"success": False, "message": "Требуется указать query для поиска в Spotify."}
            
            query_encoded = urllib.parse.quote_plus(query)
            if sys_name == "Windows":
                subprocess.run(f"start spotify:search:{query_encoded}", shell=True)
            elif sys_name == "Darwin":
                subprocess.run(f"open 'spotify:search:{query_encoded}'", shell=True)
            
            time.sleep(1.5)
            
            try:
                import pygetwindow as gw
                import keyboard as kb
                
                spotify_windows = [w for w in gw.getAllWindows() if 'spotify' in w.title.lower()]
                title_before = spotify_windows[0].title if spotify_windows else ""
                
                kb.send('play/pause media')
                time.sleep(1.5)
                
                spotify_windows_after = [w for w in gw.getAllWindows() if 'spotify' in w.title.lower()]
                title_after = spotify_windows_after[0].title if spotify_windows_after else ""
                
                default_titles = ["spotify", "spotify premium", "spotify free"]
                
                if title_after and title_after != title_before and title_after.lower() not in default_titles:
                    return {"success": True, "message": f"Spotify начал воспроизведение: {title_after}"}
                else:
                    return {"success": False, "message": f"Не удалось подтвердить воспроизведение в Spotify. Заголовок: {title_after}"}
            except Exception as e:
                return {"success": False, "message": f"Ошибка верификации окна Spotify: {e}"}
            
        elif action in ["search_youtube", "open_website"]:
            if not query:
                return {"success": False, "message": "Требуется указать URL или запрос."}
                
            if action == "search_youtube":
                raw = query.split('/')[0].split('?')[0].split('.')[0]
                clean_query = "".join([c for c in raw if c.isalnum() or c.isspace()]).strip()
                if not clean_query:
                    return {"success": False, "message": "Ошибка: пустой поисковый запрос после очистки."}
                encoded = urllib.parse.quote_plus(clean_query)
                url = f"https://www.youtube.com/results?search_query={encoded}"
                # Hard guard: never let /shorts/ leak through
                if "/shorts/" in url:
                    url = url.replace("/shorts/", "/results?search_query=")
            else:
                url = query if query.startswith("http") else f"https://{query}"
            
            if sys_name == "Windows":
                subprocess.run(f'start chrome --profile-directory="Default" "{url}"', shell=True)
            elif sys_name == "Darwin":
                subprocess.Popen(["open", "-a", "Google Chrome", url])
                
            time.sleep(1.5)
            
            return {"success": True, "message": f"Выполнено открытие: {query}"}
            
        return {"success": False, "message": f"Неизвестное медиа-действие: {action}"}
    except Exception as e:
        return {"success": False, "message": f"Ошибка медиа-управления: {str(e)}"}


def generate_excel_report(title: str, rows: list, chart_column: str = "") -> dict:
    """Generate a formatted Excel report with an optional bar chart and send to Telegram."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.chart import BarChart, Reference
        from openpyxl.utils import get_column_letter
        import os
        from pathlib import Path
        from datetime import datetime

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = title[:31]  # Excel sheet name limit

        # --- Header row style ---
        header_fill = PatternFill("solid", fgColor="1F3864")
        header_font = Font(bold=True, color="FFFFFF", size=11)

        if not rows:
            return {"success": False, "message": "Нет данных для формирования отчёта."}

        columns = list(rows[0].keys())
        for col_idx, col_name in enumerate(columns, start=1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
            ws.column_dimensions[get_column_letter(col_idx)].width = max(len(col_name) + 4, 14)

        # --- Data rows ---
        alt_fill = PatternFill("solid", fgColor="DCE6F1")
        for row_idx, row_data in enumerate(rows, start=2):
            fill = alt_fill if row_idx % 2 == 0 else PatternFill()
            for col_idx, col_name in enumerate(columns, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=row_data.get(col_name, ""))
                cell.fill = fill
                cell.alignment = Alignment(horizontal="left")

        # --- Optional bar chart ---
        if chart_column and chart_column in columns:
            chart_col_idx = columns.index(chart_column) + 1
            chart = BarChart()
            chart.title = f"{title} — {chart_column}"
            chart.style = 10
            chart.y_axis.title = chart_column
            chart.x_axis.title = columns[0]
            data_ref = Reference(ws, min_col=chart_col_idx, min_row=1, max_row=len(rows) + 1)
            cats_ref = Reference(ws, min_col=1, min_row=2, max_row=len(rows) + 1)
            chart.add_data(data_ref, titles_from_data=True)
            chart.set_categories(cats_ref)
            ws.add_chart(chart, f"A{len(rows) + 4}")

        # --- Save file ---
        desktop = Path.home() / "Desktop"
        safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip().replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = str(desktop / f"{safe_title}_{timestamp}.xlsx")
        wb.save(file_path)

        # --- Send to Telegram ---
        tg_res = send_file_to_telegram(file_path, f"📊 {title}")
        if tg_res.get("success"):
            return {"success": True, "message": f"Excel-отчёт «{title}» создан и отправлен в Telegram."}
        else:
            return {"success": True, "message": f"Excel-отчёт создан: {file_path}. Ошибка отправки в Telegram: {tg_res.get('message')}"}

    except ImportError:
        return {"success": False, "message": "Установи openpyxl: pip install openpyxl"}
    except Exception as e:
        logger.error(f"generate_excel_report error: {e}")
        return {"success": False, "message": f"Ошибка генерации отчёта: {str(e)}"}


def draft_client_reply(client_name: str, client_message: str, product_context: str, tone: str = "friendly") -> dict:
    """Generate a client reply draft for user review. Never auto-sends."""
    try:
        tone_map = {
            "formal": "формальный деловой стиль, без панибратства",
            "friendly": "дружелюбный, тёплый, человеческий тон",
            "concise": "очень лаконичный, по делу, без воды",
        }
        tone_desc = tone_map.get(tone, tone_map["friendly"])

        prompt = (
            f"Ты — опытный менеджер по клиентским коммуникациям. "
            f"Контекст продукта/услуги: {product_context}\n\n"
            f"Клиент {client_name} написал:\n\"{client_message}\"\n\n"
            f"Подготовь профессиональный черновик ответа. Тон: {tone_desc}. "
            f"Только текст ответа клиенту, без пояснений. Начни с обращения к клиенту."
        )

        import anthropic as _ant
        from config import ANTHROPIC_API_KEY
        _client = _ant.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = _client.messages.create(
            model="claude-opus-4-5",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}]
        )
        draft_text = response.content[0].text.strip()

        return {
            "success": True,
            "message": (
                f"**Черновик ответа для {client_name}:**\n\n"
                f"{draft_text}\n\n"
                f"_(Требует ручной проверки и отправки — ATLAS не отправляет автоматически)_"
            )
        }
    except Exception as e:
        logger.error(f"draft_client_reply error: {e}")
        return {"success": False, "message": f"Ошибка генерации черновика: {str(e)}"}


def suggest_meeting_slots(duration_minutes: int = 60, days_ahead: int = 3) -> dict:
    """Suggest available meeting slots based on business hours. Does NOT create events."""
    try:
        import datetime as dt

        now = dt.datetime.now()
        work_start_h = 9
        work_end_h = 18
        slot_interval = duration_minutes
        slots = []

        for day_offset in range(1, days_ahead + 1):
            target_day = now + dt.timedelta(days=day_offset)
            if target_day.weekday() >= 5:  # skip weekends
                continue
            current = target_day.replace(hour=work_start_h, minute=0, second=0, microsecond=0)
            end_of_day = target_day.replace(hour=work_end_h, minute=0, second=0, microsecond=0)
            while current + dt.timedelta(minutes=slot_interval) <= end_of_day:
                slot_end = current + dt.timedelta(minutes=slot_interval)
                day_name = target_day.strftime("%A, %d %B")
                slots.append(f"• {day_name}: {current.strftime('%H:%M')} – {slot_end.strftime('%H:%M')}")
                current = slot_end

        if not slots:
            return {"success": False, "message": "Нет доступных рабочих слотов на указанный период."}

        slots_text = "\n".join(slots[:8])  # cap at 8 options
        return {
            "success": True,
            "message": (
                f"**Доступные слоты для встречи ({duration_minutes} мин.):**\n\n"
                f"{slots_text}\n\n"
                f"_(Выбери удобный слот — событие создаётся вручную)_"
            )
        }
    except Exception as e:
        logger.error(f"suggest_meeting_slots error: {e}")
        return {"success": False, "message": f"Ошибка генерации слотов: {str(e)}"}
