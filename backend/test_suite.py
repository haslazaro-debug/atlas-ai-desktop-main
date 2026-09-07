import os
import sys
import io
import time
import logging
import pyautogui
from unittest.mock import patch, MagicMock

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(
    filename="test_results.log",
    filemode="w",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
test_logger = logging.getLogger("test_suite")

import agent_core
import tools

called_tools = []

def track_tool(tool_name):
    def wrapper(*args, **kwargs):
        called_tools.append({"tool": tool_name, "args": args, "kwargs": kwargs})
        if tool_name == "open_app":
            return {"success": True, "message": f"Mock opened {args or kwargs}"}
        if tool_name == "generate_invoice_pdf":
            return {"success": True, "message": "Mock invoice generated", "path": "mock.pdf"}
        return "mock_success"
    return wrapper

TEST_CASES = [
    # open_app
    {"cmd": "открой хром", "expected_tool": "open_app", "desc": "open_app (direct RU)"},
    {"cmd": "мне нужен браузер", "expected_tool": "open_app", "desc": "open_app (conversational RU)"},
    {"cmd": "launch Spotify player", "expected_tool": "open_app", "desc": "open_app (mixed EN)"},
    
    # search_web
    {"cmd": "поищи в интернете свежие новости ИИ", "expected_tool": "search_web", "desc": "search_web (direct search RU)"},
    {"cmd": "погугли новости о квантовых компьютерах", "expected_tool": "search_web", "desc": "search_web (conversational RU)"},
    {"cmd": "search news about Apple AI", "expected_tool": "search_web", "desc": "search_web (direct EN)"},
    
    # screenshot
    {"cmd": "сделай скриншот экрана", "expected_tool": "screenshot", "desc": "screenshot (direct RU)"},
    {"cmd": "take a screen snapshot", "expected_tool": "screenshot", "desc": "screenshot (direct EN)"},
    
    # click (Safety confirmation triggered)
    {"cmd": "кликни по координатам 400 300", "expected_tool": "click", "desc": "click (direct RU)"},
    {"cmd": "нажми мышкой на 100 200", "expected_tool": "click", "desc": "click (conversational RU)"},
    {"cmd": "click at coordinates 850 600", "expected_tool": "click", "desc": "click (direct EN)"},
    
    # type (Safety confirmation triggered)
    {"cmd": "напечатай Привет мир", "expected_tool": "type", "desc": "type (direct RU)"},
    {"cmd": "введи с клавиатуры test message", "expected_tool": "type", "desc": "type (conversational RU)"},
    {"cmd": "type hello on keyboard", "expected_tool": "type", "desc": "type (direct EN)"},
    
    # press (Safety confirmation triggered)
    {"cmd": "нажми клавишу enter", "expected_tool": "press", "desc": "press (direct RU)"},
    {"cmd": "жмякни клавишу пробел", "expected_tool": "press", "desc": "press (conversational RU)"},
    {"cmd": "press escape button", "expected_tool": "press", "desc": "press (direct EN)"},
    
    # Killer scenario (Invoice)
    {"cmd": "сделай инвойс для Nordvik на 3400 евро за консультацию", "expected_tool": "generate_invoice_pdf", "desc": "generate_invoice_pdf"},

    # Direct Factual / Ambiguous / Clarifications (Expected: NONE)
    {"cmd": "кто президент Франции", "expected_tool": "NONE", "desc": "Direct knowledge answer"},
    {"cmd": "сделай это прямо сейчас", "expected_tool": "NONE", "desc": "Ambiguous instruction"},
    {"cmd": "закрой то окно", "expected_tool": "NONE", "desc": "Ambiguous window target"},

    # Impossible / Out of scope
    {"cmd": "свари мне настоящий кофе на кухне", "expected_tool": "NONE", "desc": "Physical world impossible"},
    {"cmd": "телепортируй меня в Париж", "expected_tool": "NONE", "desc": "Sci-fi impossible"}
]

def run_tests():
    global called_tools
    print("\n" + "="*85)
    print(f"{'ATLAS AGENT CORE AUTOMATED TEST SUITE (STABILIZED)':^85}")
    print("="*85)
    print(f"{'#':<3} | {'Command':<32} | {'Expected':<15} | {'Actual':<15} | {'Result':<8}")
    print("-" * 85)

    passed = 0
    total = len(TEST_CASES)

    for idx, test in enumerate(TEST_CASES, 1):
        called_tools.clear()
        agent_core.conversation_history = []
        agent_core.pending_action = None

        cmd = test["cmd"]
        expected = test["expected_tool"]

        with patch.object(tools, 'open_app', side_effect=track_tool('open_app')), \
             patch.object(tools, 'search_web', side_effect=track_tool('search_web')), \
             patch.object(tools, 'take_screenshot', side_effect=track_tool('screenshot')), \
             patch.object(tools, 'generate_invoice_pdf', side_effect=track_tool('generate_invoice_pdf')), \
             patch.object(pyautogui, 'click', side_effect=track_tool('click')), \
             patch.object(pyautogui, 'write', side_effect=track_tool('type')), \
             patch.object(pyautogui, 'press', side_effect=track_tool('press')):

            try:
                response = agent_core.execute_command(cmd, mode="text")
            except Exception as exc:
                response = {"text": f"CRASH: {exc}", "image_path": None}

        actual = "NONE"
        if called_tools:
            actual = called_tools[0]["tool"]
        elif agent_core.pending_action and isinstance(agent_core.pending_action, dict):
            actual = agent_core.pending_action.get("type", "NONE")
        elif "собираюсь кликнуть" in response.get("text", "").lower() or "кликнут" in response.get("text", "").lower():
            actual = "click"
        elif "собираюсь напечатать" in response.get("text", "").lower() or "собираюсь ввести" in response.get("text", "").lower() or "напечатан" in response.get("text", "").lower():
            actual = "type"
        elif "собираюсь нажать" in response.get("text", "").lower() or "нажат" in response.get("text", "").lower():
            actual = "press"

        is_pass = (actual.lower() == expected.lower())
        if is_pass:
            passed += 1
            status = "\033[92mPASS\033[0m"
        else:
            status = "\033[91mFAIL\033[0m"
            test_logger.error(
                f"\n--- FAIL: Case #{idx} [{test['desc']}] ---\n"
                f"Command: '{cmd}'\n"
                f"Expected: {expected} | Actual: {actual}\n"
                f"Pending Action State: {agent_core.pending_action}\n"
                f"Agent Text Response: {response.get('text')}\n"
            )

        cmd_display = (cmd[:29] + "...") if len(cmd) > 32 else cmd
        print(f"{idx:<3} | {cmd_display:<32} | {expected:<15} | {actual:<15} | {status}")
        time.sleep(0.2)

    score = (passed / total) * 100
    print("-" * 85)
    print(f"Summary: {passed}/{total} Passed ({score:.1f}%)")
    if score >= 85:
        print("\033[92m[✓] Core Agent Tool-Use is STABLE (Meets DoD >= 85%)\033[0m\n")
    else:
        print("\033[91m[✗] Under target threshold. Check backend/test_results.log for details.\033[0m\n")

if __name__ == "__main__":
    run_tests()
