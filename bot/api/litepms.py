# bot/api/litepms.py
import aiohttp
import logging
from datetime import date, datetime
from typing import Dict, List, Union, Any, Optional

from bot.config import BASE_URL, LITEPMS_LOGIN, LITEPMS_API_KEY, SPA_ROOM_ID, DOPY_INCOME_ID

logger = logging.getLogger(__name__)

# --- Глобальная сессия для переиспользования соединений ---
_http_session: Optional[aiohttp.ClientSession] = None

async def get_session() -> aiohttp.ClientSession:
    """Возвращает глобальную aiohttp.ClientSession, создавая её при первом вызове."""
    global _http_session
    if _http_session is None or _http_session.closed:
        _http_session = aiohttp.ClientSession()
        logger.debug("🌐 Создана новая aiohttp.ClientSession")
    return _http_session

# --- Универсальная функция запроса ---
async def _request(method: str, params: dict = None, use_post: bool = False) -> dict:
    """
    Универсальная функция для выполнения GET или POST запросов к Lite PMS API.
    """
    params = params or {}
    params.update({"login": LITEPMS_LOGIN, "hash": LITEPMS_API_KEY})

    session = await get_session()
    url = f"{BASE_URL}/{method}"

    try:
        if use_post:
            async with session.post(url, data=params) as resp:
                logger.debug(f"POST {url} с параметрами: {params}")
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"Ошибка HTTP {resp.status} при POST {method}: {error_text}")
                    return {"status": "error", "data": error_text}
                data = await resp.json()
        else:
            async with session.get(url, params=params) as resp:
                logger.debug(f"GET {url} с параметрами: {params}")
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"Ошибка HTTP {resp.status} при GET {method}: {error_text}")
                    return {"status": "error", "data": error_text}
                data = await resp.json()

        # Унифицированная проверка успешности ответа
        if not isinstance(data, dict):
            logger.error(f"Неверный формат ответа от {method}: ожидался dict, получен {type(data)}")
            return {"status": "error", "data": "Неверный формат ответа от API"}

        # Lite PMS может возвращать "status" или "success"
        if data.get("status") == "success" or data.get("success") == "true":
            return data
        else:
            error_msg = data.get("data", "Неизвестная ошибка или некорректный ответ от API.")
            logger.warning(f"API {method} вернул ошибку: {error_msg}")
            return {"status": "error", "data": error_msg}

    except aiohttp.ClientError as e:
        logger.error(f"Сетевая ошибка при вызове {method}: {e}")
        return {"status": "error", "data": f"Сетевая ошибка: {e}"}
    except Exception as e:
        logger.critical(f"Неожиданная ошибка в _request({method}): {e}", exc_info=True)
        return {"status": "error", "data": f"Внутренняя ошибка: {e}"}

# --- Rooms ---
async def fetch_rooms() -> Dict[str, dict]:
    """Получает список всех номеров из Lite PMS с полной информацией."""
    data = await _request("getRooms")
    if data.get("status") == "success":
        return {str(room["id"]): room for room in data["data"]}
    logger.error(f"Ошибка fetch_rooms: {data}")
    return {}

# --- Categories ---
async def fetch_categories() -> Dict[str, str]:
    """Получает список всех категорий номеров из Lite PMS."""
    data = await _request("getCategories")
    if data.get("status") == "success":
        return {str(cat["id"]): cat["name"] for cat in data["data"]}
    logger.error(f"Ошибка fetch_categories: {data}")
    return {}

# --- Bookings ---
async def search_checkins(from_date: str, to_date: str) -> List[dict]:
    """Ищет заезды в указанный период."""
    data = await _request("searchBooking", {
        "from_date": from_date,
        "to_date": to_date,
        "type": "checkin"
    }, use_post=True)
    if data.get("status") == "success":
        return data.get("data", [])
    logger.error(f"Ошибка search_checkins: {data}")
    return []

# --- Cashbox ---
async def get_cashbox_transactions(from_date: str, to_date: str) -> List[dict]:
    """Получает кассовые операции за период."""
    data = await _request("getCashboxTransaction", {
        "from_date": from_date,
        "to_date": to_date,
    }, use_post=True)
    if data.get("status") == "success":
        return data.get("data", [])
    logger.error(f"Ошибка get_cashbox_transactions: {data}")
    return []

async def add_cashbox_transaction(
    price: float,
    type: int,
    comment: str,
    income_id: str = None,
    expense_id: str = None,
    booking_id: int = None
) -> dict:
    """
    Создаёт кассовую операцию.
    type: 0 — доход, 1 — расход
    """
    data = {
        "price": abs(price),
        "type": type,
        "comment": comment
    }
    if type == 0 and income_id:
        data["income_id"] = income_id
    elif type == 1 and expense_id:
        data["expense_id"] = expense_id
    if booking_id:
        data["booking_id"] = booking_id

    result = await _request("addCashboxTransaction", data, use_post=True)
    if result.get("success") != "true":
        error_msg = result.get("data", "Неизвестная ошибка или некорректный ответ от API.")
        logger.error(f"Ошибка add_cashbox_transaction: {error_msg}")
        raise RuntimeError(f"Lite PMS вернул ошибку: {error_msg}")
    return result

# --- Cleaning ---
async def set_cleaning_status(room_id: str, status_id: str = "0") -> dict:
    """Устанавливает статус уборки для номера или спального места."""
    result = await _request("setRoomCleaningStatus", {
        "room_id": room_id,
        "status_id": status_id
    }, use_post=True)
    if result.get("success") != "true":
        error_msg = result.get("data", "Неизвестная ошибка или некорректный ответ от API.")
        logger.error(f"Ошибка set_cleaning_status для room_id={room_id}: {error_msg}")
        raise RuntimeError(f"Lite PMS вернул ошибку: {error_msg}")
    return result

# --- Helpers ---
def format_guest_name(booking: dict) -> str:
    """Форматирует имя гостя из данных бронирования."""
    surname = str(booking.get("client_surname", "")).strip()
    name = str(booking.get("client_name", "")).strip()
    if surname and name:
        return f"{surname} {name[0]}."
    elif surname:
        return surname
    elif name:
        return name
    else:
        return "Гость без имени"

def is_active_status(status_id: str) -> bool:
    """Проверяет, является ли статус активным."""
    return status_id in ("2", "6", "8")

def get_room_name(room_id: str, rooms_cache: dict) -> str:
    """Возвращает название номера по его ID, используя кэш."""
    room_data = rooms_cache.get(room_id, {})
    if isinstance(room_data, dict):
        return room_data.get("name", f"ID {room_id}")
    elif isinstance(room_data, str):
        return room_data
    else:
        return f"ID {room_id}"

# --- Функция для получения номеров по категориям ---
async def fetch_rooms_by_categories(category_names: List[str]) -> Dict[str, str]:
    """Получает номера, принадлежащие указанным категориям."""
    # Получаем все категории
    all_categories = await fetch_categories()
    
    # Находим ID нужных категорий
    target_category_ids = [
        cat_id for cat_id, cat_name in all_categories.items()
        if cat_name in category_names
    ]
    
    if not target_category_ids:
        logger.warning(f"Не найдены категории с именами: {category_names}")
        return {}

    # Получаем все номера (полные данные)
    all_rooms = await fetch_rooms()
    
    # Фильтруем номера по категориям
    filtered_rooms = {}
    for room_id, room_data in all_rooms.items():
        cat_id = str(room_data.get("cat_id", ""))
        if cat_id in target_category_ids:
            filtered_rooms[room_id] = room_data["name"]
    
    return filtered_rooms