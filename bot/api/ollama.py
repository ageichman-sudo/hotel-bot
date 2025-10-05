import asyncio
import logging
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)
OLLAMA_URL = "http://localhost:11434/api/generate"

async def ask_ollama(
    prompt: str,
    context: str = "",
    model: str = "qwen3:8b",
    temperature: float = 0.3,
    timeout_seconds: int = 300
) -> str:
    full_prompt = f"{context}\n\nВопрос: {prompt}\nОтвет:"
    try:
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                OLLAMA_URL,
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {"temperature": temperature, "num_ctx": 2048}
                }
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("response", "").strip()
                else:
                    error_text = await resp.text()
                    logger.error(f"Ollama error: {error_text}")
                    return "❌ Ollama вернул ошибку."
    except asyncio.TimeoutError:
        return "⚠️ Таймаут: ИИ не ответил."
    except aiohttp.ClientConnectorError:
        return "⚠️ Ollama не запущен. Выполните: `ollama serve`"
    except Exception as e:
        logger.error(f"Ошибка Ollama: {e}", exc_info=True)
        return "⚠️ Ошибка ИИ-модуля."
