# bot/utils/permissions.py

from bot.auth.roles import USER_ROLES, PERMISSIONS

def get_user_role(user_id: int) -> str:
    """Получает роль пользователя по его chat_id."""
    return USER_ROLES.get(user_id)

def has_permission(user_id: int, permission: str) -> bool:
    """Проверяет, есть ли у пользователя с указанной ролью разрешение."""
    role = get_user_role(user_id)
    if not role:
        return False
    perms = PERMISSIONS.get(role, [])
    # Предполагается, что "view_all" дает все права
    return "view_all" in perms or permission in perms

def can_access_command(user_id: int, command: str) -> bool:
    """
    Проверяет, может ли пользователь выполнить команду, основываясь на сопоставлении
    команды с необходимым разрешением.
    """
    # Сопоставление команд и необходимых разрешений
    command_perms_map = {
        "/start": "view_basic",
        "/today_tomorrow": "view_bookings",
        "/room": "view_bookings",
        "/spa": "view_bookings",
        "/dop": "cash_operations",
        "/cash": "cash_operations",
        "/task": "tasks_manage",
        "/done": "tasks_manage",
        "/tasks": "tasks_manage",
        "/ask": "use_ai",
        "/send_cleaning_report": "send_cleaning_report",
        "/arrival": "arrival",
        "/arrival2": "arrival2", 
        # Добавьте другие команды и соответствующие им разрешения
    }

    required_perm = command_perms_map.get(command)
    if not required_perm:
        # Если команда не найдена в карте, решите: разрешить или запретить по умолчанию
        # Для безопасности лучше запретить
        print(f"[WARNING] Permission mapping not found for command '{command}'. Access denied.")
        return False

    return has_permission(user_id, required_perm)
