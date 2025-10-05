# main.py
import asyncio
import logging
from dotenv import load_dotenv
load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# Импорт настроек
from bot.config import BOT_TOKEN
from bot.rag.search import init_rag 

# Импорт роутеров
from bot.handlers.base import router as base_router
from bot.handlers.bookings import router as bookings_router
from bot.handlers.finance import router as finance_router
from bot.handlers.tasks import router as tasks_router
from bot.handlers.voice import router as voice_router
from bot.handlers.cleaning_report import router as cleaning_report_router

# Импорт и инициализация кэша
from bot.cache import initialize_cache, periodic_cache_refresh

# Управление ИИ
from bot.config import USE_LOCAL_AI
AI_ROUTER_AVAILABLE = False
if USE_LOCAL_AI:
    try:
        from bot.handlers.ai import router as ai_router
        AI_ROUTER_AVAILABLE = True
    except Exception as e:
        logging.error(f"❌ Ошибка импорта ai_router: {e}")
else:
    logging.info("ℹ️ ИИ отключен через .env (USE_LOCAL_AI=false)")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    if not BOT_TOKEN:
        logger.critical("❌ Не задан TELEGRAM_BOT_TOKEN в .env")
        return

    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Инициализация глобального кэша
    logger.info("🔄 Инициализация глобального кэша...")
    try:
        await initialize_cache()
        logger.info("✅ Глобальный кэш инициализирован.")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации кэша: {e}")

    # Запуск фоновой задачи обновления кэша
    cache_refresh_task = asyncio.create_task(periodic_cache_refresh(3600))
    logger.info("🚀 Задача периодического обновления кэша запущена.")

    # Подключение роутеров
    dp.include_router(base_router)
    dp.include_router(bookings_router)
    dp.include_router(finance_router)
    dp.include_router(tasks_router)
    dp.include_router(voice_router)
    dp.include_router(cleaning_report_router)
    
    if AI_ROUTER_AVAILABLE:
        dp.include_router(ai_router)
        logger.info("✅ Роутер ИИ (/ask) подключен.")
    else:
        logger.info("ℹ️ Роутер ИИ (/ask) НЕ подключен.")

    logger.info("🚀 Бот запущен и готов принимать команды.")
    try:
        await dp.start_polling(bot)
    finally:
        # Отменяем фоновую задачу при завершении
        logger.info("🛑 Отмена задачи обновления кэша...")
        cache_refresh_task.cancel()
        try:
            await cache_refresh_task
        except asyncio.CancelledError:
            logger.info("✅ Задача обновления кэша отменена.")
        logger.info("🛑 Бот остановлен.")
        
 # Инициализация RAG
    try:
        await init_rag()
        logger.info("✅ RAG инициализирован.")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации RAG: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем.")
    except Exception as e:
        logger.critical(f"💥 Критическая ошибка в main(): {e}", exc_info=True)
