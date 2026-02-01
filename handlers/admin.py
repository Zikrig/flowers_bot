from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import datetime
from config import Config
from database import Database
from google_sheets import GoogleSheets

router = Router()
db = Database()
sheets = GoogleSheets()


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id in Config.ADMIN_IDS


@router.message(Command("admin"))
async def admin_menu(message: Message):
    """Главное меню администратора"""
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав администратора.")
        return
    
    text = (
        "🔐 Панель администратора\n\n"
        "Выберите действие:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Все заказы", callback_data="admin_all_orders")],
        [
            InlineKeyboardButton(text="⏳ Ожидают оплаты", callback_data="admin_pending"),
            InlineKeyboardButton(text="✅ Оплаченные", callback_data="admin_paid")
        ],
        [
            InlineKeyboardButton(text="📅 Заказы на сегодня", callback_data="admin_today"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")
        ],
        [InlineKeyboardButton(text="🔍 Найти заказ", callback_data="admin_search_order")]
    ])
    
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "admin_all_orders")
async def admin_all_orders(callback: CallbackQuery):
    """Показать все заказы"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    orders = await db.get_all_orders()
    
    if not orders:
        await callback.message.answer("Заказов пока нет.")
        await callback.answer()
        return
    
    text = "📋 Все заказы:\n\n"
    
    for order_number, order in sorted(orders.items(), key=lambda x: x[1].get("created_at", ""), reverse=True)[:20]:  # Ограничиваем 20 заказами
        status_emoji = {
            "pending_payment": "⏳",
            "paid": "✅",
            "cancelled": "❌",
            "completed": "🎉"
        }.get(order.get("status", ""), "❓")
        
        status_text = {
            "pending_payment": "Ожидает оплаты",
            "paid": "Оплачен",
            "cancelled": "Отменен",
            "completed": "Выполнен"
        }.get(order.get("status", ""), "Неизвестно")
        
        bouquets_text = ", ".join([
            f"№{b['variant']} «{b['variant_name']}» - {b['quantity']} шт."
            for b in order.get("bouquets", [])[:2]
        ])
        if len(order.get("bouquets", [])) > 2:
            bouquets_text += f" и еще {len(order.get('bouquets', [])) - 2}"
        
        text += (
            f"{status_emoji} Заказ №{order_number}\n"
            f"   Статус: {status_text}\n"
            f"   Клиент: {order.get('last_name', '')} {order.get('first_name', '')}\n"
            f"   Букеты: {bouquets_text}\n"
            f"   Самовывоз: {order.get('pickup_date', 'N/A')} в {order.get('pickup_time', 'N/A')}\n"
            f"   Сумма: {order.get('total_price', 0):,} ₽\n\n"
        )
    
    if len(orders) > 20:
        text += f"\n... и еще {len(orders) - 20} заказов"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_menu")]
    ])
    
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_pending")
async def admin_pending_orders(callback: CallbackQuery):
    """Показать заказы, ожидающие оплаты"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    orders = await db.get_all_orders()
    pending_orders = {k: v for k, v in orders.items() if v.get("status") == "pending_payment"}
    
    if not pending_orders:
        await callback.message.answer("Нет заказов, ожидающих оплаты.")
        await callback.answer()
        return
    
    text = "⏳ Заказы, ожидающие оплаты:\n\n"
    
    for order_number, order in sorted(pending_orders.items(), key=lambda x: x[1].get("created_at", ""), reverse=True):
        created_at = order.get("created_at", "")
        if created_at:
            try:
                created = datetime.fromisoformat(created_at)
                hours_passed = (datetime.now() - created).total_seconds() / 3600
                time_left = max(0, 24 - hours_passed)
                time_info = f"Осталось: {time_left:.1f} ч."
            except:
                time_info = ""
        else:
            time_info = ""
        
        text += (
            f"🔸 Заказ №{order_number}\n"
            f"   Клиент: {order.get('last_name', '')} {order.get('first_name', '')}\n"
            f"   Сумма: {order.get('total_price', 0):,} ₽\n"
            f"   {time_info}\n\n"
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_menu")]
    ])
    
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_paid")
async def admin_paid_orders(callback: CallbackQuery):
    """Показать оплаченные заказы"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    orders = await db.get_all_orders()
    paid_orders = {k: v for k, v in orders.items() if v.get("status") == "paid"}
    
    if not paid_orders:
        await callback.message.answer("Нет оплаченных заказов.")
        await callback.answer()
        return
    
    text = "✅ Оплаченные заказы:\n\n"
    
    for order_number, order in sorted(paid_orders.items(), key=lambda x: x[1].get("pickup_date", "")):
        bouquets_text = ", ".join([
            f"№{b['variant']} «{b['variant_name']}» - {b['quantity']} шт."
            for b in order.get("bouquets", [])[:2]
        ])
        
        text += (
            f"🔸 Заказ №{order_number}\n"
            f"   Клиент: {order.get('last_name', '')} {order.get('first_name', '')}\n"
            f"   Букеты: {bouquets_text}\n"
            f"   Самовывоз: {order.get('pickup_date', 'N/A')} в {order.get('pickup_time', 'N/A')}\n"
            f"   Сумма: {order.get('total_price', 0):,} ₽\n\n"
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_menu")]
    ])
    
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_today")
async def admin_today_orders(callback: CallbackQuery):
    """Показать заказы на сегодня"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    today = datetime.now().date()
    orders = await db.get_all_orders()
    
    from utils import parse_date_string
    
    today_orders = []
    for order_number, order in orders.items():
        pickup_date_str = order.get("pickup_date", "")
        pickup_date_obj = parse_date_string(pickup_date_str)
        if pickup_date_obj and pickup_date_obj.date() == today:
            today_orders.append((order_number, order))
    
    if not today_orders:
        await callback.message.answer("На сегодня заказов нет.")
        await callback.answer()
        return
    
    text = f"📅 Заказы на сегодня ({today.strftime('%d.%m.%Y')}):\n\n"
    
    for order_number, order in sorted(today_orders, key=lambda x: x[1].get("pickup_time", "")):
        bouquets_text = ", ".join([
            f"№{b['variant']} «{b['variant_name']}» - {b['quantity']} шт. - {b['count']} {'букет' if b['count'] == 1 else 'букета' if b['count'] in [2, 3, 4] else 'букетов'}"
            for b in order.get("bouquets", [])
        ])
        
        status_emoji = "✅" if order.get("status") == "paid" else "⏳"
        
        text += (
            f"{status_emoji} Заказ №{order_number}\n"
            f"   Время: {order.get('pickup_time', 'N/A')}\n"
            f"   Клиент: {order.get('last_name', '')} {order.get('first_name', '')}\n"
            f"   Букеты: {bouquets_text}\n"
            f"   Сумма: {order.get('total_price', 0):,} ₽\n\n"
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_menu")]
    ])
    
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats_handler(callback: CallbackQuery):
    """Показать статистику заказов"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    orders = await db.get_all_orders()
    
    total_orders = len(orders)
    pending = sum(1 for o in orders.values() if o.get("status") == "pending_payment")
    paid = sum(1 for o in orders.values() if o.get("status") == "paid")
    cancelled = sum(1 for o in orders.values() if o.get("status") == "cancelled")
    
    total_revenue = sum(o.get("total_price", 0) for o in orders.values() if o.get("status") == "paid")
    
    text = (
        "📊 Статистика заказов:\n\n"
        f"Всего заказов: {total_orders}\n"
        f"⏳ Ожидают оплаты: {pending}\n"
        f"✅ Оплачено: {paid}\n"
        f"❌ Отменено: {cancelled}\n\n"
        f"💰 Общая выручка: {total_revenue:,} ₽"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_menu")]
    ])
    
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_search_order")
async def admin_search_order(callback: CallbackQuery, state: FSMContext):
    """Поиск заказа по номеру"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.answer(
        "Введите номер заказа для поиска:\n"
        "Например: 042"
    )
    await callback.answer()
    
    # Устанавливаем флаг в состоянии
    await state.update_data(admin_searching=True)


@router.callback_query(F.data == "admin_menu")
async def admin_menu_callback(callback: CallbackQuery):
    """Вернуться в главное меню администратора"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    text = (
        "🔐 Панель администратора\n\n"
        "Выберите действие:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Все заказы", callback_data="admin_all_orders")],
        [
            InlineKeyboardButton(text="⏳ Ожидают оплаты", callback_data="admin_pending"),
            InlineKeyboardButton(text="✅ Оплаченные", callback_data="admin_paid")
        ],
        [
            InlineKeyboardButton(text="📅 Заказы на сегодня", callback_data="admin_today"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")
        ],
        [InlineKeyboardButton(text="🔍 Найти заказ", callback_data="admin_search_order")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.message(F.text.regexp(r'^\d{3}$'))
async def admin_order_found(message: Message, state: FSMContext):
    """Показать информацию о найденном заказе"""
    if not is_admin(message.from_user.id):
        return
    
    # Проверяем, что администратор ищет заказ
    data = await state.get_data()
    if not data.get("admin_searching"):
        return
    
    order_number = message.text
    order = await db.get_order(order_number)
    
    if not order:
        await message.answer(f"Заказ №{order_number} не найден.")
        await state.update_data(admin_searching=False)
        return
    
    bouquets_text = ", ".join([
        f"№{b['variant']} «{b['variant_name']}» - {b['quantity']} шт. - {b['count']} {'букет' if b['count'] == 1 else 'букета' if b['count'] in [2, 3, 4] else 'букетов'}"
        for b in order.get("bouquets", [])
    ])
    
    status_text = {
        "pending_payment": "⏳ Ожидает оплаты",
        "paid": "✅ Оплачен",
        "cancelled": "❌ Отменен",
        "completed": "🎉 Выполнен"
    }.get(order.get("status", ""), "❓ Неизвестно")
    
    text = (
        f"📋 Информация о заказе №{order_number}\n\n"
        f"Статус: {status_text}\n"
        f"Клиент: {order.get('last_name', '')} {order.get('first_name', '')}\n"
        f"Ник: @{order.get('username', 'N/A')}\n"
        f"Telegram ID: {order.get('user_id', 'N/A')}\n\n"
        f"Букеты: {bouquets_text}\n"
        f"Самовывоз: {order.get('pickup_date', 'N/A')} в {order.get('pickup_time', 'N/A')}\n"
        f"Сумма: {order.get('total_price', 0):,} ₽\n\n"
        f"Создан: {order.get('created_at', 'N/A')[:19] if order.get('created_at') else 'N/A'}\n"
    )
    
    if order.get("refund_card"):
        text += f"Карта для возврата: {order.get('refund_card')}\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_menu")]
    ])
    
    await message.answer(text, reply_markup=keyboard)
    await state.update_data(admin_searching=False)
