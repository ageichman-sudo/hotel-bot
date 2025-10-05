# bot/handlers/cleaning_report.py
import logging
from datetime import datetime
from typing import List, Dict, Any, Union

from aiogram import Router, F
from aiogram.types import Message, ContentType
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# Импорты настроек, кэша, API
from bot.config import CLEANING_REPORTS_CHANNEL_ID, CLEANING_ZONES
from bot.api.litepms import set_cleaning_status

router = Router()
logger = logging.getLogger(__name__)

# FSM States
class CleaningReportState(StatesGroup):
    waiting_for_zone_selection = State()
    waiting_for_files = State()
    waiting_for_comment = State()

REPORT_DATA_KEY = "cleaning_report_data"

def get_zone_display_name(zone_name: str, room_id_in_litepms: Union[str, None]) -> str:
    """Возвращает отображаемое имя зоны."""
    if room_id_in_litepms:
        return f"{zone_name}"
    return zone_name

# Хендлер на команду или кнопку "🧼 Отчет по уборке"
@router.message(F.text == "🧼 Отчет по уборке")
@router.message(Command("cleaning_report"))
async def start_cleaning_report(message: Message, state: FSMContext):
    """Начинает процесс создания отчета об уборке."""
    user_id = message.from_user.id   

    if not CLEANING_ZONES:
        await message.answer("❌ Список зон уборки не настроен. Обратитесь к администратору.")
        logger.warning("Список зон уборки (CLEANING_ZONES) пуст при попытке отправить отчет.")
        return

    # Создаем клавиатуру с зонами
    kb = ReplyKeyboardBuilder()
    for zone_name, room_id_in_litepms in CLEANING_ZONES:
        display_name = get_zone_display_name(zone_name, room_id_in_litepms)
        kb.button(text=display_name)
    kb.button(text="❌ Отмена")
    kb.adjust(2)

    await message.answer("Выберите зону, которую убрали:", reply_markup=kb.as_markup(resize_keyboard=True))
    await state.set_state(CleaningReportState.waiting_for_zone_selection)

# Хендлер: Кнопка "❌ Отмена" на этапе выбора зоны
@router.message(StateFilter(CleaningReportState.waiting_for_zone_selection), F.text == "❌ Отмена")
async def cancel_zone_selection(message: Message, state: FSMContext):
    """Отмена выбора зоны и выход из процесса отчета."""
    await state.clear()
    await message.answer("↩️ Отправка отчета по уборке отменена.")

# Хендлер выбора зоны
@router.message(StateFilter(CleaningReportState.waiting_for_zone_selection))
async def process_zone_selection(message: Message, state: FSMContext):
    """Обрабатывает выбор зоны уборки."""
    if message.text == "⬅️ Назад":
        await start_cleaning_report(message, state)
        return

    selected_zone_text = message.text.strip()
    
    # Найти зону по отображаемому имени
    selected_zone = None
    for zone_name, room_id_in_litepms in CLEANING_ZONES:
        display_name = get_zone_display_name(zone_name, room_id_in_litepms)
        if display_name == selected_zone_text:
            selected_zone = (zone_name, room_id_in_litepms)
            break
            
    if not selected_zone:
        # Пробуем по оригинальному имени
        for zone_name, room_id_in_litepms in CLEANING_ZONES:
            if zone_name == selected_zone_text:
                selected_zone = (zone_name, room_id_in_litepms)
                break

    if not selected_zone:
        await message.answer("❌ Выбрана неизвестная зона. Пожалуйста, выберите из списка.")
        return

    zone_name, room_id_in_litepms = selected_zone
    await state.update_data({
        REPORT_DATA_KEY: {
            "zone_name": zone_name,
            "room_id_in_litepms": room_id_in_litepms,
            "files": [],
            "comment": "",
            "timestamp": datetime.now().isoformat()
        }
    })

    # Создаем клавиатуру с кнопкой "Готово" и "Назад"
    kb = ReplyKeyboardBuilder()
    kb.button(text="✅ Готово")
    kb.button(text="⬅️ Назад")
    kb.adjust(2)

    await message.answer(
        "Прикрепите фото/видео/документы отчета об уборке.\n"
        "Когда закончите — нажмите кнопку '✅ Готово'.\n"
        "Чтобы выбрать другую зону — нажмите '⬅️ Назад'.",
        reply_markup=kb.as_markup(resize_keyboard=True)
    )
    await state.set_state(CleaningReportState.waiting_for_files)

# Хендлер: Кнопка "⬅️ Назад" на этапе прикрепления файлов
@router.message(StateFilter(CleaningReportState.waiting_for_files), F.text == "⬅️ Назад")
async def go_back_from_files(message: Message, state: FSMContext):
    """Возвращает пользователя к выбору зоны."""
    await state.clear()
    await start_cleaning_report(message, state)

# Хендлер сбора файлов
@router.message(StateFilter(CleaningReportState.waiting_for_files), ~F.text.startswith("✅"))
async def collect_files(message: Message, state: FSMContext):
    """Собирает файлы, пока пользователь не нажмет '✅ Готово'."""
    user_data = await state.get_data()
    report_data = user_data.get(REPORT_DATA_KEY, {})
    
    if 'files' not in report_data:
        report_data['files'] = []

    file_id = None
    file_type = None
    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = 'photo'
    elif message.video:
        file_id = message.video.file_id
        file_type = 'video'
    elif message.document:
        file_id = message.document.file_id
        file_type = 'document'

    if file_id and file_type:
        report_data['files'].append({
            'file_id': file_id,
            'file_type': file_type
        })
        await state.update_data({REPORT_DATA_KEY: report_data})
        logger.info(f"Файл {file_type} от пользователя {message.from_user.id} добавлен в отчет.")
    else:
        await message.answer("Пожалуйста, прикрепите фото, видео или документ.")

# Хендлер завершения сбора файлов
@router.message(StateFilter(CleaningReportState.waiting_for_files), F.text == "✅ Готово")
async def finish_collecting_files(message: Message, state: FSMContext):
    """Завершает сбор файлов и переходит к комментарию."""
    user_data = await state.get_data()
    report_data = user_data.get(REPORT_DATA_KEY, {})
    
    if not report_data.get('files'):
        await message.answer("Вы не прикрепили ни одного файла. Пожалуйста, прикрепите фото/видео/документы.")
        return

    # Создаем клавиатуру с кнопкой "Пропустить" и "Назад"
    kb = ReplyKeyboardBuilder()
    kb.button(text="⏭️ Пропустить")
    kb.button(text="⬅️ Назад")
    kb.adjust(2)

    await message.answer(
        "Файлы получены.\n"
        "Хотите добавить текстовый комментарий?\n"
        "Если нет — нажмите '⏭️ Пропустить'.\n"
        "Чтобы прикрепить другие файлы — нажмите '⬅️ Назад'.",
        reply_markup=kb.as_markup(resize_keyboard=True)
    )
    await state.set_state(CleaningReportState.waiting_for_comment)

# Хендлер: Кнопка "⬅️ Назад" на этапе ожидания комментария
@router.message(StateFilter(CleaningReportState.waiting_for_comment), F.text == "⬅️ Назад")
async def go_back_from_comment(message: Message, state: FSMContext):
    """Возвращает пользователя к этапу прикрепления файлов."""
    user_data = await state.get_data()
    report_data = user_data.get(REPORT_DATA_KEY, {})
    if 'comment' in report_data:
        del report_data['comment']
    await state.update_data({REPORT_DATA_KEY: report_data})

    kb = ReplyKeyboardBuilder()
    kb.button(text="✅ Готово")
    kb.button(text="⬅️ Назад")
    kb.adjust(2)

    await message.answer(
        "Прикрепите фото/видео/документы отчета об уборке.\n"
        "Когда закончите — нажмите кнопку '✅ Готово'.\n"
        "Чтобы выбрать другую зону — нажмите '⬅️ Назад'.",
        reply_markup=kb.as_markup(resize_keyboard=True)
    )
    await state.set_state(CleaningReportState.waiting_for_files)

# Хендлер: Кнопка "⏭️ Пропустить" на этапе ожидания комментария
@router.message(StateFilter(CleaningReportState.waiting_for_comment), F.text == "⏭️ Пропустить")
async def skip_comment(message: Message, state: FSMContext):
    """Пропускает ввод комментария и завершает отчет."""
    user_data = await state.get_data()
    report_data = user_data.get(REPORT_DATA_KEY, {})
    await state.update_data({REPORT_DATA_KEY: report_data})
    await process_final_step(message, state)

# Хендлер получения комментария и завершения отчета
@router.message(StateFilter(CleaningReportState.waiting_for_comment))
async def process_comment_input(message: Message, state: FSMContext):
    """Обрабатывает ввод комментария, отправляет отчет и обновляет статус."""
    user_data = await state.get_data()
    report_data = user_data.get(REPORT_DATA_KEY, {})
    if not report_data:
        await message.answer("❌ Ошибка. Начните сначала.")
        await state.clear()
        return

    comment = message.text.strip()
    if comment.lower() != "нет":
        report_data['comment'] = comment
    await state.update_data({REPORT_DATA_KEY: report_data})
    await process_final_step(message, state)

# --- Функция: Финальная обработка (отправка отчета, обновление статуса) ---
async def process_final_step(message: Message, state: FSMContext):
    """Выполняет финальные шаги: отправка отчета и обновление статуса уборки."""
    user_data = await state.get_data()
    report_data = user_data.get(REPORT_DATA_KEY, {})
    if not report_data:
        await message.answer("❌ Ошибка. Начните сначала.")
        await state.clear()
        return

    # --- Отправка отчета в канал ---
    channel_id = CLEANING_REPORTS_CHANNEL_ID
    if not channel_id:
        await message.answer("❌ Не удалось отправить отчет: не задан `CLEANING_REPORTS_CHANNEL_ID` в `.env`.")
        await state.clear()
        logger.error("CLEANING_REPORTS_CHANNEL_ID не задан в .env при попытке отправить отчет по уборке.")
        return

    try:
        zone_name = report_data['zone_name']
        room_id_in_litepms = report_data.get('room_id_in_litepms')
        timestamp_str = report_data['timestamp']
        dt_obj = datetime.fromisoformat(timestamp_str)
        formatted_datetime = dt_obj.strftime('%d.%m.%Y %H:%M')

        caption_parts = [
            f"🧼 <b>Отчет об уборке</b>",
            f"<b>Зона:</b> {zone_name}",
            f"<b>ID в LitePMS:</b> {room_id_in_litepms or '-'}",
            f"<b>Время:</b> {formatted_datetime}",
            f"<b>Отправитель:</b> {message.from_user.full_name} (ID: {message.from_user.id})"
        ]
        if report_data['comment']:
            caption_parts.append(f"<b>Комментарий:</b> {report_data['comment']}")

        caption = "\n".join(caption_parts)

        files_data: List[Dict[str, str]] = report_data.get('files', [])
        if not files_data:
             raise ValueError("Нет прикрепленных файлов для отправки.")

        # --- Оптимизация: сначала текст, потом медиагруппа ---
        # 1. Отправляем подпись как отдельное сообщение
        sent_caption_message = await message.bot.send_message(
            chat_id=channel_id,
            text=caption,
            parse_mode=ParseMode.HTML
        )
        logger.info(f"Подпись отчета по уборке зоны '{zone_name}' отправлена в канал ({channel_id}), message_id: {sent_caption_message.message_id}")

        # 2. Отправляем все файлы как медиагруппу
        from aiogram.types import InputMediaPhoto, InputMediaVideo, InputMediaDocument
        media_group = []
        for file_info in files_data:
            fid = file_info['file_id']
            ftype = file_info['file_type']
            if ftype == 'photo':
                media_group.append(InputMediaPhoto(media=fid))
            elif ftype == 'video':
                media_group.append(InputMediaVideo(media=fid))
            else:
                media_group.append(InputMediaDocument(media=fid))
        
        if media_group:
            try:
                sent_media_group = await message.bot.send_media_group(
                    chat_id=channel_id,
                    media=media_group
                )
                logger.info(f"Медиагруппа из {len(media_group)} файл(ов) отчета по уборке зоны '{zone_name}' отправлена в канал ({channel_id}).")
            except Exception as e:
                logger.error(f"Ошибка при отправке медиагруппы файлов отчета по уборке зоны '{zone_name}': {e}")
                await message.answer("⚠️ Ошибка при отправке файлов отчета.")
        else:
            await message.answer("📭 Нет файлов для отправки в медиагруппу.")

    except ValueError as ve:
        specific_error_msg = str(ve)
        logger.error(f"Ошибка при подготовке к отправке отчета по уборке зоны '{zone_name}': {specific_error_msg}")
        await message.answer(f"❌ Ошибка: {specific_error_msg}")
        await state.clear()
        return
    except Exception as e:
        logger.error(f"Ошибка при отправке отчета по уборке зоны '{zone_name}' в канал: {e}", exc_info=True)
        await message.answer("⚠️ Не удалось отправить отчет. Попробуйте позже.")
        await state.clear()
        return # Прерываем дальнейшую обработку, если не удалось отправить

    # --- Обновление статуса уборки в Lite PMS ---
    room_id_in_litepms = report_data.get('room_id_in_litepms')
    if room_id_in_litepms:
        try:
            result = await set_cleaning_status(room_id=room_id_in_litepms, status_id="0")
            if result is None:
                 logger.error(f"Функция set_cleaning_status вернула None для room_id={room_id_in_litepms}")
                 await message.answer("⚠️ Произошла ошибка при обновлении статуса уборки в системе (пустой ответ от API).")
            elif result.get("status") == "success":
                logger.info(f"Статус уборки для номера/зоны {room_id_in_litepms} обновлен на 'Чистый'.")
                # Не отправляем сообщение пользователю, если он не админ, чтобы не дублировать.
                # await message.answer("✅ Статус уборки зоны в системе обновлен на 'Чистый'.")
            else:
                # Обрабатываем ошибку от API
                error_msg = result.get("data", "Неизвестная ошибка или некорректный ответ от API.")
                logger.error(f"Ошибка обновления статуса уборки для {room_id_in_litepms}: {error_msg}")
                # await message.answer(f"⚠️ Не удалось обновить статус уборки в системе: {error_msg}")
        except Exception as e:
            logger.error(f"Исключение при обновлении статуса уборки в Lite PMS для {room_id_in_litepms}: {e}", exc_info=True)
            # await message.answer(f"⚠️ Произошла ошибка при обновлении статуса уборки в системе: {e}")
    else:
        logger.info(f"Для зоны '{report_data['zone_name']}' не указан ID в LitePMS. Статус уборки не обновлялся.")

    await state.clear()
    # Отправляем уведомление пользователю
    await message.answer(f"✅ Отчет по уборке зоны **{report_data['zone_name']}** отправлен в канал.")