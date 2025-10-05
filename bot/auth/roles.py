# bot/config/roles.py

# Пример: chat_id → роль
USER_ROLES = {
    719582469: "manager",      # управляющий (ANTON)
    987654321: "admin",        # администратор (MYHILLS)
    445980456: "admin",        # Олеся
    882514266: "admin",        # Ангелина
    5251516574: "admin",       # Лена
    1689963297: "admin",       # Валя Т
    8084441371: "housekeeper",  # Ирина
    6514788343: "housekeeper",  # Наташа
    6242527551: "housekeeper",  # Аня
    838089481: "housekeeper",  # Света
    5164612943: "technician",  # Роман
    8101695296: "technician",  # Максим
    474427349: "technician",  # Юра
}

# Права для каждой роли
PERMISSIONS = {
    "manager": ["view_all"],
    "admin": [
        "tasks_manage",
        "cleaning_schedule",
        "cleaning_spa_schedule",
        "cash_operations",
        "view_bookings",
        "send_cleaning_report",
        "arrival",
        "spa"
    ],
    "housekeeper": [
        "cleaning_schedule",
        "cleaning_spa_schedule",
        "report_cleaning",
        "send_cleaning_report",
        "arrival",
        "spa"
    ],
    "technician": [
        "tasks_repair",
    ],
}
