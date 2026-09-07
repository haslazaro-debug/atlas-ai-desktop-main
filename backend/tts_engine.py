import os
import re
import urllib.parse
import edge_tts

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

EDGE_RU_VOICE = "ru-RU-DmitryNeural"
EDGE_EN_VOICE = "en-US-ChristopherNeural"


def clean_tts_text(text: str) -> str:
    clean = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    clean = re.sub(r"[*#_>`\[\]()]", "", clean)
    clean = re.sub(r"https?://\S+", "", clean)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


def has_cyrillic(text: str) -> bool:
    return bool(re.search(r"[А-Яа-яЁё]", text))


async def stream_audio_generator(text: str):
    clean_text = clean_tts_text(text)
    if not clean_text:
        return

    try:
        voice = EDGE_RU_VOICE if has_cyrillic(clean_text) else EDGE_EN_VOICE
        communicate = edge_tts.Communicate(clean_text, voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]
    except Exception as e:
        print(f"TTS error: {e}")


async def generate_speech(text: str) -> str | None:
    """
    Returns a dynamic streaming endpoint URL instead of downloading and saving.
    """
    if not text:
        return None
    clean_text = clean_tts_text(text)
    if not clean_text:
        return None
        
    return f"http://localhost:8000/api/tts_stream?text={urllib.parse.quote(clean_text)}"
