import time
import logging
from sales_engine import load_business_knowledge

logger = logging.getLogger("atlas.ai_brain")

# ---------------------------------------------------------------------------
# In-memory stores & configurations
# ---------------------------------------------------------------------------
conversation_memory: dict[str, dict] = {}
last_message_time: dict[str, float] = {}

SESSION_TTL = 86400        # Сессия сбрасывается, если клиент молчит более 24 часов
RATE_LIMIT_SECONDS = 2.0   # Защита от спама: минимум 2 секунды между сообщениями
SYSTEM_SALES_PROMPT = """
Ты — ATLAS, элитный ИИ-менеджер по продажам. Твоя задача — вести клиента к сделке по методологиям SPIN и Challenger, опираясь СТРОГО на базу знаний бизнеса.

ЖЕСТКИЕ ПРАВИЛА БЕЗОПАСНОСТИ И ЭСКАЛАЦИИ:
1. НИЧЕГО НЕ ВЫДУМЫВАЙ. Если клиент спрашивает то, чего нет в твоей базе знаний (например, индивидуальные скидки, нестандартные услуги, точные свободные часы, которых нет в таблице), ТЫ НЕ ИМЕЕШЬ ПРАВА ПРИДУМЫВАТЬ ОТ СЕБЯ.
2. ФЛАГ ЭСКАЛАЦИИ: Если информации в базе нет или клиент просит нестандартные условия, твой ответ ДОЛЖЕН начинаться со служебного тега [NEED_HUMAN], после чего напиши вежливую заглушку клиенту (например: «Этот вопрос лучше уточню у руководителя, секунду!»). Система автоматически уведомит владельца бизнеса.
3. Во всех остальных случаях (когда данные есть в базе) отвечай уверенно, используя SPIN-вопросы и удержание ценности (Challenger).
4. Отвечай на языке клиента: русский → русский, English → English.

БАЗА ЗНАНИЙ И УСЛОВИЯ БИЗНЕСА:
{business_knowledge}
"""

def check_rate_limit(customer_id: str) -> bool:
    """Ограничивает слишком частые сообщения от одного пользователя (защита от спама)."""
    now = time.time()
    if customer_id in last_message_time:
        if now - last_message_time[customer_id] < RATE_LIMIT_SECONDS:
            return False
    last_message_time[customer_id] = now
    return True


def generate_sales_response(business_id: str, customer_id: str, incoming_message: str) -> dict:
    """
    Генерирует ответ с учетом памяти, TTL сессии, антиспама и методологий продаж.
    """
    import anthropic
    from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

    # 1. Проверка на спам
    if not check_rate_limit(customer_id):
        logger.warning(f"[ai_brain] Сработал Rate Limit для клиента {customer_id}")
        return {
            "status": "rate_limited",
            "reply": "",
            "business_id": business_id,
            "customer_id": customer_id,
        }

    memory_key = f"{business_id}_{customer_id}"
    current_time = time.time()

    # Проверяем и очищаем сессию, если прошло больше 24 часов
    if memory_key in conversation_memory:
        if current_time - conversation_memory[memory_key]["last_active"] > SESSION_TTL:
            del conversation_memory[memory_key]
            logger.info(f"[ai_brain] Сессия устарела и сброшена для business={business_id} customer={customer_id}")

    if memory_key not in conversation_memory:
        conversation_memory[memory_key] = {"history": [], "last_active": current_time}

    session = conversation_memory[memory_key]
    session["last_active"] = current_time
    history = session["history"]

    knowledge = load_business_knowledge(business_id)
    system_prompt = SYSTEM_SALES_PROMPT.format(business_knowledge=knowledge)

    messages = list(history)
    messages.append({"role": "user", "content": incoming_message})

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=400,
            system=system_prompt,
            messages=messages
        )

        raw_reply = response.content[0].text.strip()

        # Detect escalation flag and strip it from the customer-facing text
        needs_human = "[NEED_HUMAN]" in raw_reply
        clean_reply = raw_reply.replace("[NEED_HUMAN]", "").strip()

        # Persist this turn in memory (store the clean reply, not the raw tag)
        history.append({"role": "user", "content": incoming_message})
        history.append({"role": "assistant", "content": clean_reply})

        # Rolling window: keep last 20 messages (10 turns)
        if len(history) > 20:
            session["history"] = history[-20:]

        status = "escalate_to_human" if needs_human else "auto_reply"
        logger.info(f"[ai_brain] business={business_id} customer={customer_id} status={status} ({len(clean_reply)} chars)")

        return {
            "status": status,
            "reply": clean_reply,
            "business_id": business_id,
            "customer_id": customer_id,
        }

    except Exception as e:
        logger.error(f"[ai_brain] Error for business={business_id}: {e}")
        return {
            "status": "error",
            "reply": "Извините, небольшой технический сбой. Менеджер уже подключается к диалогу!",
            "business_id": business_id,
            "customer_id": customer_id,
        }



def clear_conversation(business_id: str, customer_id: str) -> None:
    """Resets the conversation history for a specific customer."""
    memory_key = f"{business_id}_{customer_id}"
    if memory_key in conversation_memory:
        del conversation_memory[memory_key]
        logger.info(f"[ai_brain] Conversation reset for business={business_id} customer={customer_id}")


def get_conversation_summary(business_id: str, customer_id: str) -> list[dict]:
    """Returns the raw conversation history (for admin review/export)."""
    memory_key = f"{business_id}_{customer_id}"
    return conversation_memory.get(memory_key, {}).get("history", [])
