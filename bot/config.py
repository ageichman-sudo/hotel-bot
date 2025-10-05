# bot/config.py
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logger = logging.getLogger(__name__)

# Обязательные параметры
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
LITEPMS_LOGIN = os.getenv("LITEPMS_LOGIN")
LITEPMS_API_KEY = os.getenv("LITEPMS_API_KEY")

if not BOT_TOKEN:
    raise ValueError("❌ Не задан TELEGRAM_BOT_TOKEN в .env")
if not LITEPMS_LOGIN:
    raise ValueError("❌ Не задан LITEPMS_LOGIN в .env")
if not LITEPMS_API_KEY:
    raise ValueError("❌ Не задан LITEPMS_API_KEY в .env")


USE_LOCAL_AI = os.getenv("USE_LOCAL_AI", "false").lower() == "true"
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
CLEANING_REPORTS_CHANNEL_ID_RAW = os.getenv("CLEANING_REPORTS_CHANNEL_ID")
try:
    CLEANING_REPORTS_CHANNEL_ID = int(CLEANING_REPORTS_CHANNEL_ID_RAW) if CLEANING_REPORTS_CHANNEL_ID_RAW else None
except (ValueError, TypeError):
    logger.error(f"❌ Неверный формат CLEANING_REPORTS_CHANNEL_ID в .env: {CLEANING_REPORTS_CHANNEL_ID_RAW}")
    CLEANING_REPORTS_CHANNEL_ID = None

# Список зон для отчетов об уборке из .env
CLEANING_ZONES_RAW = os.getenv("CLEANING_ZONES", "")
CLEANING_ZONES = []
if CLEANING_ZONES_RAW:
    try:
        zones_raw_list = CLEANING_ZONES_RAW.split(';')
        for zone_part in zones_raw_list:
            zone_part = zone_part.strip()
            if ':' in zone_part:
                name, room_id = zone_part.rsplit(':', 1)
                CLEANING_ZONES.append((name.strip(), room_id.strip()))
            else:
                CLEANING_ZONES.append((zone_part, None))
        logger.info(f"✅ Загружено {len(CLEANING_ZONES)} зон уборки из .env")
    except Exception as e:
        logger.error(f"❌ Ошибка парсинга CLEANING_ZONES из .env: {e}")
        CLEANING_ZONES = []
else:
    logger.warning("⚠️ Список зон уборки (CLEANING_ZONES) не задан в .env")
    CLEANING_ZONES = []

#Категории для arrivals
ARRIVAL_CATEGORIES_RAW = os.getenv("ARRIVAL_CATEGORIES", "")
ARRIVAL_CATEGORIES = [cat.strip() for cat in ARRIVAL_CATEGORIES_RAW.split(",") if cat.strip()]

# Константы
BASE_URL = "https://litepms.ru/api"
DB_PATH = Path("tasks.db")
SPA_ROOM_ID = "49518"
DOPY_INCOME_ID = "9534"
FAQ_PATH = Path("faq.json")
