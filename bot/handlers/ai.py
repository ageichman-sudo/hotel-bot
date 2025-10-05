# bot/handlers/ai.py
from aiogram import Router, types
from aiogram.filters import Command

from bot.config import USE_LOCAL_AI, FAQ_PATH
from bot.utils.db import get_active_tasks

router = Router()

if USE_LOCAL_AI:
    from bot.api.ollama import ask_ollama

# bot/handlers/ai.py
from aiogram import Router, types
from aiogram.filters import Command
from bot.rag import rag_ask_ollama

router = Router()

@router.message(Command("ask"))
async def cmd_ask(message: types.Message):

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Пример: `/ask Кто убирает СПА сегодня?`", parse_mode="Markdown")
        return

    user_question = args[1].strip()

    # Формируем контекст (можно расширить)
    context = f"Сегодня {message.date.strftime('%d.%m.%Y')}."

    try:
        answer = await rag_ask_ollama(user_question, context)
        await message.answer(answer, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")