# bot/rag/search.py
import logging
from typing import List, Dict

from bot.rag.faq_loader import load_faq
from bot.rag.vector_store import search_similar_questions, add_faq_entries, init_vector_store
from bot.api.ollama import ask_ollama

logger = logging.getLogger(__name__)

# Флаг инициализации
RAG_INITIALIZED = False

async def init_rag():
    """Инициализирует RAG: загружает FAQ, создаёт векторную БД."""
    global RAG_INITIALIZED
    if RAG_INITIALIZED:
        return

    try:
        # Инициализация Chroma и модели
        await init_vector_store()

        # Загрузка FAQ
        faq_data = load_faq()

        # Добавление в векторную БД
        add_faq_entries(faq_data)

        RAG_INITIALIZED = True
        logger.info("✅ RAG инициализирован.")
    except Exception as e:
        logger.error(f"Ошибка инициализации RAG: {e}", exc_info=True)
        raise

async def find_relevant_faq_entries(query: str, top_k: int = 3) -> List[Dict[str, str]]:
    """Ищет похожие записи в FAQ через векторный поиск."""
    try:
        await init_rag()  # Убедимся, что RAG инициализирован
        return search_similar_questions(query, top_k)
    except Exception as e:
        logger.error(f"Ошибка поиска в FAQ через RAG: {e}", exc_info=True)
        return []

async def rag_ask_ollama(user_question: str, context: str = "") -> str:
    """
    Отправляет запрос в Ollama с контекстом из FAQ.
    """
    try:
        # Поиск похожих вопросов в FAQ
        faq_results = await find_relevant_faq_entries(user_question, top_k=3)

        # Формируем контекст из найденных записей
        faq_context = ""
        if faq_results:
            faq_lines = ["🔍 Найденные ответы в базе знаний:"]
            for item in faq_results:
                faq_lines.append(f"Вопрос: {item['question']}\nОтвет: {item['answer']}\n")
            faq_context = "\n".join(faq_lines)

        # Объединяем контексты
        full_context = f"{context}\n\n{faq_context}".strip()

        # Отправляем в Ollama
        return await ask_ollama(user_question, full_context)
    except Exception as e:
        logger.error(f"Ошибка в rag_ask_ollama: {e}", exc_info=True)
        return "❌ Произошла ошибка при обращении к ИИ."