hotel-bot/
├── .env                          # 🔐 Переменные окружения (токены, логины, ID)
├── .gitignore                    # 📦 Игнорируемые файлы для Git
├── requirements.txt              # 🧩 Зависимости Python
├── main.py                       # 🚀 Точка входа: запуск бота, подключение роутеров
├── README.md                     # 📖 Документация проекта
├── logs/                         # 📝 Логи работы бота (создаются автоматически)
│   ├── stdout.log
│   └── stderr.log
├── tasks.db                      # 🗃️ Локальная база данных задач (SQLite)
├── faq.json                      # ❓ База знаний для ИИ (вопрос-ответ)
├── bot/
│   ├── __init__.py               # 🧱 Инициализация пакета bot
│   ├── config.py                 # ⚙️ Настройки бота (чтение .env, константы)
│   ├── cache.py                  # 🔄 Кэширование данных (номера, справочники)
│   ├── handlers/                 # 🎮 Обработчики команд Telegram
│   │   ├── __init__.py
│   │   ├── base.py               # 🏠 Главное меню, /start
│   │   ├── bookings.py           # 📅 /arrival, /room, /spa
│   │   ├── finance.py            # 💰 /dopy — доходы по статье 9534
│   │   ├── tasks.py              # ✅ /task, /done, /tasks — система задач
│   │   ├── cleaning_report.py    # 🧼 /cleaning_report — отчеты об уборке
│   │   ├── voice.py              # 🎙 Обработка голосовых сообщений
│   │   └── ai.py                 # 🤖 /ask — ИИ-ассистент (Ollama + RAG)
│   ├── api/                      # 🔌 Интеграция с внешними API
│   │   ├── __init__.py
│   │   ├── litepms.py            # 🏨 Работа с Lite PMS API
│   │   └── ollama.py             # 🧠 Работа с локальным ИИ (Ollama)
│   └── utils/                    # 🛠 Вспомогательные функции
│       ├── __init__.py
│       ├── db.py                 # 🗄 Работа с SQLite (задачи, пользователи)
│       ├── permissions.py        # 🔐 Система ролей и прав доступа
│       └── voice.py              # 🎤 Распознавание речи (Whisper + ffmpeg)