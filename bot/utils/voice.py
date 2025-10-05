import asyncio
import logging
import os
import subprocess
import tempfile
from functools import partial

WHISPER_AVAILABLE = False
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    logging.warning("Whisper не установлен.")

logger = logging.getLogger(__name__)
WHISPER_MODEL = None

def load_whisper_model():
    global WHISPER_MODEL
    if WHISPER_MODEL is None:
        logger.info("Загрузка модели Whisper 'base'...")
        WHISPER_MODEL = whisper.load_model("base")
    return WHISPER_MODEL

async def convert_ogg_to_wav(ogg_path: str) -> str:
    wav_path = ogg_path.replace(".ogg", ".wav")
    try:
        result = subprocess.run([
            "ffmpeg", "-i", ogg_path,
            "-ar", "16000",
            "-ac", "1",
            "-f", "wav",
            "-y",
            wav_path
        ], capture_output=True, text=True, check=True, timeout=30)
        return wav_path
    except subprocess.TimeoutExpired:
        raise RuntimeError("ffmpeg: таймаут")
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка ffmpeg: {e.stderr}")
        raise
    except FileNotFoundError:
        raise RuntimeError("ffmpeg не найден. Установите FFmpeg и добавьте в PATH.")

async def transcribe_voice(ogg_bytes: bytes) -> str:
    if not WHISPER_AVAILABLE:
        raise RuntimeError("Whisper не установлен")

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as ogg_file:
        ogg_file.write(ogg_bytes)
        ogg_path = ogg_file.name

    try:
        wav_path = await asyncio.wait_for(convert_ogg_to_wav(ogg_path), timeout=30.0)
        model = load_whisper_model()
        loop = asyncio.get_event_loop()
        # Исправленный вызов
        transcribe_func = partial(model.transcribe, language="ru")
        result = await loop.run_in_executor(None, transcribe_func, wav_path)
        return result["text"].strip()

    finally:
        for p in [ogg_path, wav_path]:
            if os.path.exists(p):
                os.remove(p)
