# bot/handlers/tasks.py
from aiogram import Router, types
from aiogram.filters import Command

from bot.utils.db import create_task, get_active_tasks, complete_task, get_task_room_id
from bot.api.litepms import set_cleaning_status

router = Router()

@router.message(Command("task"))
async def cmd_task(message: types.Message):
    """Создаёт новую задачу."""

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Пример: `/task Уборка СПА`")
        return

    desc = args[1].strip()
    task_id = create_task(desc, str(message.from_user.id))
    await message.answer(f"✅ Задача #{task_id} создана.\nЗавершить: `/done {task_id}`")
    
    # --- ИСПРАВЛЕНИЕ: await внутри async def ---
    # Возвращаем к админ-меню
    from .base import cmd_admin_menu
    await cmd_admin_menu(message)
    # ------------------------------------------


@router.message(Command("done"))
async def cmd_done(message: types.Message):
    """Помечает задачу как выполненную."""
   
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Пример: `/done 5`")
        return

    try:
        task_id = int(args[1])
    except ValueError:
        await message.answer("ID должен быть числом.")
        return

    room_id = get_task_room_id(task_id)
    if not room_id:
        await message.answer(f"❌ Задача #{task_id} не найдена.")
        # Возвращаем к админ-меню и выходим
        from .base import cmd_admin_menu
        await cmd_admin_menu(message)
        return

    updated = complete_task(task_id)

    if room_id and room_id.isdigit():
        try:
            await set_cleaning_status(room_id, "0")
        except Exception as e:
            await message.answer(f"⚠️ Статус уборки не обновлён: {e}")

    await message.answer(f"✅ Задача #{task_id} завершена.")
    
    # --- ИСПРАВЛЕНИЕ: await внутри async def ---
    # Возвращаем к админ-меню
    from .base import cmd_admin_menu
    await cmd_admin_menu(message)
    # ------------------------------------------


@router.message(Command("tasks"))
async def cmd_tasks(message: types.Message):
    """Показывает список активных задач."""
    
    rows = get_active_tasks()
    if not rows:
        await message.answer("📭 Нет активных задач.")
        # Возвращаем к админ-меню и выходим
        from .base import cmd_admin_menu
        await cmd_admin_menu(message)
        return

    lines = ["📋 Активные задачи:\n"]
    for tid, desc, rname in rows:
        lines.append(f"• #{tid}: {desc}")
        if rname:
            lines.append(f"  🏨 {rname}")
        lines.append("")

    await message.answer("\n".join(lines))
    
    # --- ИСПРАВЛЕНИЕ: await внутри async def ---
    # Возвращаем к админ-меню
    from .base import cmd_admin_menu
    await cmd_admin_menu(message)
    # ------------------------------------------
