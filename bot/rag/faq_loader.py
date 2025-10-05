# bot/rag/faq_loader.py
import json
import logging
from pathlib import Path
from typing import List, Dict

FAQ_PATH = Path("faq.json")
logger = logging.getLogger(__name__)

# Глобальный кэш FAQ
FAQ_CACHE: List[Dict[str, str]] = []
FAQ_CACHE_LOADED = False

def load_faq(force_reload: bool = False) -> List[Dict[str, str]]:
    """Загружает FAQ из JSON-файла и кэширует."""
    global FAQ_CACHE, FAQ_CACHE_LOADED
    if FAQ_CACHE_LOADED and not force_reload:
        return FAQ_CACHE

    if not FAQ_PATH.exists():
        logger.warning(f"FAQ файл не найден: {FAQ_PATH}")
        FAQ_CACHE = []
        FAQ_CACHE_LOADED = True
        return []

    try:
        with open(FAQ_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                FAQ_CACHE = data
            else:
                logger.error("Неверный формат faq.json: ожидается список объектов.")
                FAQ_CACHE = []
    except Exception as e:
        logger.error(f"Ошибка загрузки FAQ: {e}", exc_info=True)
        FAQ_CACHE = []

    FAQ_CACHE_LOADED = True
    logger.info(f"Загружено {len(FAQ_CACHE)} записей из FAQ.")
    return FAQ_CACHE