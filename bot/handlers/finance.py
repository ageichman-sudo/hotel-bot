from aiogram import Router, types
from aiogram.filters import Command
from datetime import date, datetime

from bot.api.litepms import get_cashbox_transactions, add_cashbox_transaction
from bot.utils.permissions import can_access_command  # ← НОВОЕ: проверка прав

router = Router()

# --- /dop ---
@router.message(Command("dop"))
async def cmd_dop(message: types.Message):
    user_id = message.from_user.id

    # Проверка прав
    if not can_access_command(user_id, "/dop"):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        target_date = date.today()
    else:
        date_str = args[1].strip()
        try:
            target_date = datetime.strptime(date_str, "%Y.%m.%d").date()
        except ValueError:
            await message.answer(
                "❌ Неверный формат даты.\n"
                "Используйте: `/dop 2025.09.26`",
                parse_mode="Markdown"
            )
            return

    date_iso = target_date.isoformat()
    transactions = await get_cashbox_transactions(date_iso, date_iso)

    TARGET_INCOME_ID = "9534"  # или используйте bot.config.DOP_INCOME_ID, если есть
    filtered = []
    for tx in transactions:
        try:
            price = float(tx.get("price", 0))
            income_id = str(tx.get("income", {}).get("id", ""))
            if price > 0 and income_id == TARGET_INCOME_ID:
                filtered.append(tx)
        except (ValueError, TypeError, AttributeError):
            continue

    if not filtered:
        await message.answer(f"Нет поступлений по статье «допы» за {target_date.strftime('%d.%m.%Y')}.")
        return

    lines = [f"💰 Поступления по статье «допы» за {target_date.strftime('%d.%m.%Y')}:\n"]
    for tx in filtered:
        time_str = tx.get("date", "")[11:16]  # "14:30"
        amount = float(tx.get("price", 0))
        comment = tx.get("comment", "").strip() or "—"
        amount_fmt = f"{int(amount):,} ₽".replace(",", " ")
        lines.append(f"🕒 {time_str} | {amount_fmt} | {comment}")

    full_text = "\n".join(lines)
    if len(full_text) > 4000:
        parts = [full_text[i:i+4000] for i in range(0, len(full_text), 4000)]
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(full_text)


# --- /cash ---
@router.message(Command("cash"))
async def cmd_cash(message: types.Message):
    user_id = message.from_user.id

    # Проверка прав
    if not can_access_command(user_id, "/cash"):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return

    # Логируем сырое сообщение
    raw_text = message.text
    print(f"[DEBUG] Получена команда: {raw_text}")

    # Разбиваем на 3 части: /cash, тип, сумма и всё остальное — комментарий
    args = message.text.split(maxsplit=2)
    print(f"[DEBUG] args после split(maxsplit=2): {args}")

    if len(args) < 3:
        print(f"[DEBUG] args < 3: len = {len(args)}")
        await message.answer(
            "💰 Создание кассовой операции\n\n"
            "Формат: `/cash [доход/расход] [сумма] [комментарий]`\n\n"
            "Пример: `/cash доход 5000 \"Оплата СПА\"`",
            parse_mode="Markdown"
        )
        return

    op_type = args[1]
    rest = args[2]

    print(f"[DEBUG] op_type: {op_type}")
    print(f"[DEBUG] rest (сумма + комментарий): {rest}")

    # Разбиваем rest на сумму и комментарий
    parts = rest.split(maxsplit=1)
    print(f"[DEBUG] parts после split(maxsplit=1): {parts}")

    if len(parts) < 1:
        await message.answer("❌ Не указана сумма.")
        return

    amount_str = parts[0]
    comment = parts[1] if len(parts) > 1 else ""

    print(f"[DEBUG] amount_str: {amount_str}")
    print(f"[DEBUG] comment: {comment}")

    if op_type.lower() not in ("доход", "расход"):
        await message.answer("❌ Укажите тип: `доход` или `расход`")
        return

    try:
        # Заменяем запятую на точку, если есть
        amount_str = amount_str.replace(",", ".")
        amount = float(amount_str)
        print(f"[DEBUG] amount: {amount}")
    except ValueError:
        print(f"[DEBUG] ValueError при float(amount_str)")
        await message.answer("❌ Сумма должна быть числом (например: 1000.50).")
        return

    # 0 — доход, 1 — расход
    type_id = 0 if op_type.lower() == "доход" else 1

    try:
        result = await add_cashbox_transaction(
            price=amount,
            type=type_id,
            comment=comment,
            # pay_type_id по умолчанию = 10874 (наличные), можно не указывать
        )
        op_id = result.get("data", [{}])[0].get("operation_id", "неизвестен")
        await message.answer(f"✅ Операция создана: ID {op_id}, {amount} ₽, '{comment}'")
        
        # --- ИСПРАВЛЕНИЕ: await внутри async def ---
        # Возвращаем к админ-меню
        from .base import cmd_admin_menu
        await cmd_admin_menu(message)
        # ------------------------------------------

    except Exception as e:
        await message.answer(f"❌ Ошибка при создании операции: {e}")      
