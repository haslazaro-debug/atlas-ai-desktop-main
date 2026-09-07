import os
import io
import logging
import tempfile
from typing import Union
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

MODEL_SIZE = "small"
INITIAL_PROMPT = "ATLAS AI voice assistant. Алматы, Астана, Windows, Discord, Telegram, YouTube, Spotify, терминал, запуск, открой, погода, блокнот, калькулятор, папочка дома, подъем."

_model = None

def get_whisper_model() -> WhisperModel:
    global _model
    if _model is None:
        try:
            import torch
            has_cuda = torch.cuda.is_available()
        except ImportError:
            has_cuda = False

        if has_cuda:
            try:
                logger.info(f"Loading faster-whisper ({MODEL_SIZE}) on CUDA (float16)...")
                _model = WhisperModel(MODEL_SIZE, device="cuda", compute_type="float16")
            except Exception as e:
                logger.warning(f"Failed to load on CUDA ({e}), falling back to CPU (int8)...")
                _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
        else:
            logger.info(f"Loading faster-whisper ({MODEL_SIZE}) on CPU (int8)...")
            _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
            
        logger.info("faster-whisper model loaded successfully.")
    return _model

def transcribe_audio(audio_input: Union[str, bytes], filename: str = "audio.webm") -> str:
    """
    Transcribes audio from a file path or raw bytes using faster-whisper.
    """
    if not audio_input:
        return ""

    temp_path = None
    target_path = None

    try:
        if isinstance(audio_input, bytes):
            if len(audio_input) < 100:
                logger.warning("[STT WARNING]: Audio byte stream too small (<100 bytes)")
                return ""
            with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1] or ".webm", delete=False) as tmp:
                tmp.write(audio_input)
                temp_path = tmp.name
            target_path = temp_path
        else:
            target_path = audio_input
            if not os.path.exists(target_path) or os.path.getsize(target_path) < 100:
                logger.warning(f"[STT WARNING]: File invalid or too small: {target_path}")
                return ""

        model = get_whisper_model()
        segments, info = model.transcribe(
            target_path,
            language="ru",
            beam_size=5,
            initial_prompt=INITIAL_PROMPT,
            vad_filter=True,
            vad_parameters=dict(threshold=0.5, min_silence_duration_ms=500)
        )

        text = " ".join([segment.text for segment in segments]).strip()
        logger.info(f'[STT RESULT] (lang={info.language}, prob={info.language_probability:.2f}): "{text}"')
        return text

    except Exception as e:
        logger.exception(f"[STT ERROR]: Whisper transcription error: {e}")
        return ""
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

def transcribe_audio_bytes(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    return transcribe_audio(audio_bytes, filename=filename)
