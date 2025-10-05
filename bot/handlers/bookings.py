# bot/handlers/bookings.py
import logging
from datetime import date, timedelta
from aiogram import Router, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from bot.config import SPA_ROOM_ID, CLEANING_ZONES, ARRIVAL_CATEGORIES
from bot.api.litepms import search_checkins, format_guest_name, is_active_status, fetch_rooms, get_room_name, fetch_categories, fetch_rooms_by_categories
# Импорт проверки прав
from bot.utils.permissions import can_access_command

router = Router()
logger = logging.getLogger(__name__)

# Глобальный кэш номеров
ROOMS_CACHE = {}

async def load_rooms_cache():
    """Загружает кэш номеров при запуске."""
    global ROOMS_CACHE
    ROOMS_CACHE = await fetch_rooms()
    logger.info(f"Загружено {len(ROOMS_CACHE)} номеров в кэш")

# --- /arrival2 ---
@router.message(Command("arrival2"))
async def cmd_arrival2(message: types.Message):
    """Отправляет список гостей, заезжающих сегодня и завтра."""
    # Проверка прав доступа
    if not can_access_command(message.from_user.id, "/arrival2"):
        await message.answer("❌ У вас нет прав для выполнения этой команды1.")
        logger.warning(f"Пользователь {message.from_user.id} попытался выполнить /arrival2 без прав.")
        return

    today = date.today()
    tomorrow = today + timedelta(days=1)
    bookings = await search_checkins(today.isoformat(), tomorrow.isoformat())

    grouped = {today.isoformat(): [], tomorrow.isoformat(): []}
    for b in bookings:
        if is_active_status(b["status_id"]):
            d = b["date_in"][:10]
            if d in grouped:
                grouped[d].append(b)

    parts = []
    for d in [today, tomorrow]:
        label = "Сегодня" if d == today else "Завтра"
        entries = grouped[d.isoformat()]
        if entries:
            lines = []
            for b in entries:
                guest = format_guest_name(b)
                # Используем кэш для получения названия номера
                from bot.cache import get_room_name
                room_name = ROOMS_CACHE.get(str(b['room_id']), f"ID {b['room_id']}")
                total_guests = int(b.get('person', 1)) + int(b.get('person_add', 0))
                lines.append(f"• {room_name} — {guest} ({total_guests} гостя)")
            parts.append(f"📅 {label}, {d.strftime('%d.%m')}:\n" + "\n".join(lines))
        else:
            parts.append(f"📅 {label}, {d.strftime('%d.%m')}:\n• Нет заездов")

    await message.answer("\n\n".join(parts))


# --- /arrival ---
@router.message(Command("arrival"))
async def cmd_arrival(message: types.Message):
    """Отправляет список гостей, заезжающих сегодня и завтра, только для указанных категорий."""
    # Проверка прав доступа
    if not can_access_command(message.from_user.id, "/arrival"):
        await message.answer("❌ У вас нет прав для выполнения этой команды1.")
        logger.warning(f"Пользователь {message.from_user.id} попытался выполнить /arrival без прав.")
        return

    if not ARRIVAL_CATEGORIES:
        await message.answer("❌ Список категорий для /arrival не настроен. Обратитесь к администратору.")
        logger.warning("Список категорий для /arrival (ARRIVAL_CATEGORIES) пуст.")
        return

    # Получаем номера только для указанных категорий
    target_rooms = await fetch_rooms_by_categories(ARRIVAL_CATEGORIES)
    if not target_rooms:
        await message.answer(f"❌ Не найдены номера в категориях: {', '.join(ARRIVAL_CATEGORIES)}")
        logger.warning(f"Не найдены номера в категориях: {ARRIVAL_CATEGORIES}")
        return

    today = date.today()
    tomorrow = today + timedelta(days=1)
    bookings = await search_checkins(today.isoformat(), tomorrow.isoformat())

    # Фильтруем только активные заезды в целевых номерах
    filtered_bookings = []
    for b in bookings:
        if is_active_status(b["status_id"]) and str(b["room_id"]) in target_rooms:
            filtered_bookings.append(b)

    # Сортируем по названию номера
    filtered_bookings.sort(key=lambda x: target_rooms.get(str(x["room_id"]), ""))

    grouped: dict[str, list] = {today.isoformat(): [], tomorrow.isoformat(): []}
    for b in filtered_bookings:
        d = b["date_in"][:10]
        if d in grouped:
            grouped[d].append(b)

    parts = []
    for d in [today, tomorrow]:
        label = "Сегодня" if d == today else "Завтра"
        entries = grouped[d.isoformat()]
        if entries:
            lines = []
            for b in entries:
                guest = format_guest_name(b)
                room_name = target_rooms.get(str(b['room_id']), f"ID {b['room_id']}")
                total_guests = int(b.get('person', 1)) + int(b.get('person_add', 0))
                lines.append(f"• {room_name} — {guest} ({total_guests} гостя)")
            parts.append(f"📅 {label}, {d.strftime('%d.%m')}:\n" + "\n".join(lines))
        else:
            parts.append(f"📅 {label}, {d.strftime('%d.%m')}:\n• Нет заездов")

    await message.answer("\n\n".join(parts))

# --- /room ---
@router.message(Command("room"))
async def cmd_room(message: types.Message):
    """Показывает заезды в конкретный номер по названию."""
    # Проверка прав доступа
    if not can_access_command(message.from_user.id, "/room"):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        logger.warning(f"Пользователь {message.from_user.id} попытался выполнить /room без прав.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Пример: `/room Дом 12`", parse_mode="Markdown")
        return

    room_query = args[1].strip().lower()
    
    # Ищем room_id по названию
    target_room_id = None
    for rid, rname in ROOMS_CACHE.items():
        if isinstance(rname, str) and rname.lower() == room_query:
            target_room_id = rid
            break
        elif isinstance(rname, list):
            for name in rname:
                if name.lower() == room_query:
                    target_room_id = rid
                    break
            if target_room_id:
                break

    if not target_room_id:
        # Попробуем частичное совпадение
        matches = []
        for rid, rnames in ROOMS_CACHE.items():
            if isinstance(rnames, list):
                rname = ", ".join(rnames).strip()
            else:
                rname = str(rnames).strip()
            if room_query in rname.lower():
                matches.append(rname)
        if matches:
            await message.answer(
                f"Номер «{room_query}» не найден. Возможно, вы имели в виду:\n" + "\n".join(f"• {m}" for m in matches)
            )
        else:
            await message.answer(f"Номер «{room_query}» не найден.")
        return

    today = date.today()
    tomorrow = today + timedelta(days=1)
    bookings = await search_checkins(today.isoformat(), tomorrow.isoformat())

    matched = []
    for b in bookings:
        if b["room_id"] == target_room_id and is_active_status(b["status_id"]):
            checkin_date = b["date_in"][:10]
            guest = format_guest_name(b)
            total_guests = int(b.get("person", 1)) + int(b.get("person_add", 0))
            matched.append((checkin_date, guest, total_guests))

    if not matched:
        room_name = ROOMS_CACHE.get(target_room_id, f"ID {target_room_id}")
        await message.answer(f"Нет заездов в «{room_name}» на сегодня и завтра.")
    else:
        lines = []
        for checkin_date, guest, guests in matched:
            d_label = "Сегодня" if checkin_date == today.isoformat() else "Завтра"
            lines.append(f"• {d_label} — {guest} ({guests} гостя)")
        room_name = ROOMS_CACHE.get(target_room_id, f"ID {target_room_id}")
        await message.answer(f"🏨 {room_name}:\n" + "\n".join(lines))


# --- /spa ---
@router.message(Command("spa"))
async def cmd_spa(message: types.Message):
    """Показывает брони СПА на 2 дня."""
    # Проверка прав доступа
    if not can_access_command(message.from_user.id, "/spa"):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        logger.warning(f"Пользователь {message.from_user.id} попытался выполнить /spa без прав.")
        return

    SPA_ID = SPA_ROOM_ID
    today = date.today()
    tomorrow = today + timedelta(days=1)
    bookings = await search_checkins(today.isoformat(), tomorrow.isoformat())

    spa_bookings = []
    for b in bookings:
        if b.get("room_id") == SPA_ID and is_active_status(b["status_id"]):
            checkin_date = b["date_in"][:10]
            checkin_time = b["date_in"][11:16]
            checkout_time = b["date_out"][11:16]
            guest = format_guest_name(b)
            total_guests = int(b.get("person", 1)) + int(b.get("person_add", 0))
            spa_bookings.append({
                "date": checkin_date,
                "time_in": checkin_time,
                "time_out": checkout_time,
                "guest": guest,
                "guests": total_guests
            })
            
    # Сортировка по времени начала   
    spa_bookings.sort(key=lambda x: x["time_in"])
    
    if not spa_bookings:
        await message.answer("Нет бронирований в СПА на сегодня и завтра.")
        return

    parts = []
    for d in [today, tomorrow]:
        d_str = d.isoformat()
        label = "Сегодня" if d == today else "Завтра"
        day_label = f"💆‍♀️ {label}, {d.strftime('%d.%m')}:"
        entries = [b for b in spa_bookings if b["date"] == d_str]
        if entries:
            lines = []
            for b in entries:
                lines.append(
                    f"• {b['guest']} ({b['guests']} гостя)\n"
                    f"  🕒 {b['time_in']} – {b['time_out']}"
                )
            parts.append(f"{day_label}\n" + "\n".join(lines))
        else:
            parts.append(f"{day_label}\n• Нет бронирований")

    await message.answer("\n\n".join(parts))