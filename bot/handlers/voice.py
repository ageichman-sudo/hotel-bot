from aiogram import Router, types
from aiogram.filters import Command
from bot.utils.voice import transcribe_voice, WHISPER_AVAILABLE
from bot.api.litepms import set_cleaning_status, fetch_rooms

router = Router()

ROOMS_CACHE = {}

@router.message(lambda message: message.voice is not None)  # ← Вот так фильтруем голосовые
async def handle_voice_message(message: types.Message):
    
    if not WHISPER_AVAILABLE:
        await message.answer("🎙 Голосовые команды недоступны (Whisper не установлен).")
        return

    global ROOMS_CACHE
    if not ROOMS_CACHE:
        ROOMS_CACHE = await fetch_rooms()

    try:
        file = await message.bot.get_file(message.voice.file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        audio_data = file_bytes.read()

        text = await transcribe_voice(audio_data)
        await message.reply(f"🎙 Распознано: _{text}_", parse_mode="Markdown")

        if any(word in text.lower() for word in ["убран", "готов", "сделан", "почищен"]):
            found_room_id = None
            found_room_name = None
            for rid, rname in ROOMS_CACHE.items():
                if rname.lower() in text.lower():
                    found_room_id = rid
                    found_room_name = rname
                    break

            if found_room_id:
                await set_cleaning_status(found_room_id, "0")
                await message.answer(f"✅ Статус уборки обновлён: {found_room_name} — чистый")
            else:
                await message.answer("❓ Не удалось определить номер. Скажите, например: «Дом 12 убран»")

    except Exception as e:
        import logging
        logging.error(f"Ошибка в обработке голоса: {e}", exc_info=True)
        await message.answer("❌ Не удалось обработать голосовое сообщение.")
