# bot/cache.py
import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from bot.api.litepms import fetch_rooms  # Предполагается, что fetch_rooms возвращает dict[str, str]

logger = logging.getLogger(__name__)

# --- Глобальный кэш ---
# Структура: {ключ_кэша: {"data": данные, "timestamp": время_загрузки}}
_cache: Dict[str, Dict[str, Any]] = {}
CACHE_LOCK = asyncio.Lock()

# Время жизни кэша по умолчанию (в секундах) - 1 час
DEFAULT_TTL = 3600

# --- Функции для работы с кэшем ---

async def _load_rooms_into_cache(ttl: int = DEFAULT_TTL):
    """Загружает список номеров в кэш."""
    try:
        rooms_dict = await fetch_rooms()
        if rooms_dict:
            _cache['rooms'] = {
                'data': rooms_dict,
                'timestamp': datetime.now(),
                'ttl': ttl
            }
            logger.info(f"✅ Кэш номеров обновлён. Загружено {len(rooms_dict)} записей.")
        else:
            logger.warning("⚠️ Получен пустой список номеров при обновлении кэша.")
    except Exception as e:
        logger.error(f"❌ Ошибка при загрузке номеров в кэш: {e}", exc_info=True)
        # Не очищаем старый кэш при ошибке, если он есть


async def initialize_cache():
    """Инициализирует кэш при запуске приложения."""
    logger.info("🔄 Инициализация глобального кэша...")
    await _load_rooms_into_cache()
    logger.info("✅ Инициализация глобального кэша завершена.")


async def refresh_cache():
    """Обновляет все данные в кэше."""
    logger.info("🔄 Обновление глобального кэша...")
    await _load_rooms_into_cache()
    logger.info("✅ Глобальный кэш обновлён.")


def get_cached_data(key: str) -> Optional[Any]:
    """
    Получает данные из кэша по ключу, если они не устарели.
    :param key: Ключ кэша (например, 'rooms').
    :return: Данные из кэша или None, если данных нет или они устарели.
    """
    cached_item = _cache.get(key)
    if not cached_item:
        return None

    data = cached_item.get('data')
    timestamp = cached_item.get('timestamp')
    ttl = cached_item.get('ttl', DEFAULT_TTL)

    if not data or not timestamp:
        return None

    if datetime.now() - timestamp > timedelta(seconds=ttl):
        logger.debug(f"ℹ️ Данные в кэше по ключу '{key}' устарели.")
        return None

    return data


def get_room_name(room_id: str) -> str:
    """
    Получает читаемое название номера по его ID из кэша.
    :param room_id: ID номера (строка, т.к. в API LitePMS часто используется строка).
    :return: Название номера или строка вида "ID {room_id}".
    """
    rooms_dict = get_cached_data('rooms')
    if rooms_dict and isinstance(rooms_dict, dict):
        # room_name в API может быть списком, берем первый элемент или саму строку
        room_name_raw = rooms_dict.get(str(room_id), f"ID {room_id}")
        if isinstance(room_name_raw, list) and room_name_raw:
            return room_name_raw[0] # Берем первое имя, если список
        elif isinstance(room_name_raw, str):
            return room_name_raw
        else:
            return f"ID {room_id}"
    return f"ID {room_id}"


# --- Функция для периодического обновления ---
async def periodic_cache_refresh(interval: int = DEFAULT_TTL):
    """
    Бесконечно обновляет кэш с заданным интервалом.
    :param interval: Интервал обновления в секундах.
    """
    while True:
        await asyncio.sleep(interval)
        await refresh_cache()
