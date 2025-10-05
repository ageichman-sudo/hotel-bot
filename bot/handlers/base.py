# bot/handlers/base.py
import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext

from bot.utils.permissions import get_user_role
#from bot.api.litepms import fetch_rooms
#from bot.cache import get_room_name

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("start"))  # <-- Исправлено: добавлен декоратор
async def cmd_start(message: types.Message):
    """Отправляет приветственное сообщение и главное меню."""
    user_id = message.from_user.id

    kb = ReplyKeyboardBuilder()

    # Основные разделы
    kb.button(text="🏨 Заезды")        # -> будет вызывать arrival
    kb.button(text="💆‍♀️ СПА")          # -> /spa
    kb.button(text="🧼 Отчет по уборке")

    # Проверяем роль пользователя для админ-меню
    user_role = get_user_role(user_id)
    if user_role == "manager":
        kb.button(text="🛠 Админ")

    kb.adjust(2) # 2 кнопки в ряд

    welcome_text = (
        "🏨 Операционный бот отеля\n\n"
        "Выберите действие:"
    )

    await message.answer(welcome_text, reply_markup=kb.as_markup(resize_keyboard=True))


# --- Навигация по основным разделам ---

@router.message(lambda message: message.text == "🏨 Заезды")
async def cmd_arrival_redirect(message: types.Message):
    """Открывает подменю 'Заезды'."""
    # Вызываем напрямую функцию из bookings.py
    try:
        from bot.handlers.bookings import cmd_arrival
        await cmd_arrival(message)
    except ImportError:
        # Если функция не найдена, отправляем команду
        await message.answer("/arrival")
    except Exception as e:
        logger.error(f"Ошибка при вызове функции заездов: {e}")
        await message.answer("⚠️ Произошла ошибка при открытии списка заездов.")


@router.message(lambda message: message.text == "💆‍♀️ СПА")
async def cmd_spa_redirect(message: types.Message):
    """Перенаправляет в команду /spa."""
    try:
        from bot.handlers.bookings import cmd_spa
        await cmd_spa(message)
    except ImportError:
        # Если функция не найдена, отправляем команду
        await message.answer("/spa")
    except Exception as e:
        logger.error(f"Ошибка при вызове меню СПА: {e}")
        await message.answer("⚠️ Произошла ошибка при открытии меню СПА.")


# --- Исправленный редирект на Отчет по уборке ---
@router.message(lambda message: message.text == "🧼 Отчет по уборке")
async def start_cleaning_report_redirect(message: types.Message):  # <-- Убран state
    """Перенаправляет в модуль отчетов по уборке."""
    from bot.utils.permissions import can_access_command
    if not can_access_command(message.from_user.id, "/send_cleaning_report"):
        await message.answer("❌ У вас нет прав для отправки отчета по уборке.")
        return

    try:
        # Импортируем команду напрямую
        from bot.handlers.cleaning_report import cmd_start_cleaning_report
        # Вызываем команду, НЕ передавая state
        await cmd_start_cleaning_report(message)  # <-- Без state
    except ImportError:
        # Если функция не найдена, отправляем команду
        await message.answer("/cleaning_report")
    except Exception as e:
        logger.error(f"Ошибка при вызове меню отчета по уборке: {e}")
        await message.answer("⚠️ Произошла ошибка при открытии меню отчета по уборке.")


# --- Админ-меню (только для manager) ---

@router.message(lambda message: message.text == "🛠 Админ")
async def cmd_show_admin_menu(message: types.Message):
    """Показывает админ-меню только управляющему."""
    user_id = message.from_user.id
    user_role = get_user_role(user_id)

    if user_role != "manager":
        await message.answer("❌ У вас нет прав для доступа к админ-меню.")
        logger.warning(f"Пользователь {user_id} (роль: {user_role}) попытался получить доступ к админ-меню.")
        return

    kb = ReplyKeyboardBuilder()
    kb.button(text="/cash")
    kb.button(text="/task")
    kb.button(text="/dopy")
    kb.button(text="/ask")
    kb.button(text="/room")  # <-- /room перемещен сюда
    kb.button(text="🔙 Назад")
    kb.adjust(2)

    await message.answer(
        "🛠 Административное меню\n\n"
        "Доступные команды:",
        reply_markup=kb.as_markup(resize_keyboard=True)
    )


# --- Кнопка "Назад" ---

@router.message(lambda message: message.text == "🔙 Назад")
async def cmd_go_back(message: types.Message):
    """Возвращает пользователя в главное меню."""
    await cmd_start(message)
