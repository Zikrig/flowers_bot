from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from config import Config
from database import Database
from google_sheets import GoogleSheets

router = Router()
db = Database()
sheets = GoogleSheets()


class CancellationStates(StatesGroup):
    """Состояния для отмены заказа"""
    confirming_cancellation = State()
    entering_refund_card = State()


@router.callback_query(F.data == "cancel_order")
async def start_cancellation(callback: CallbackQuery, state: FSMContext):
    """Начало процесса отмены заказа - показываем список заказов"""
    user_id = callback.from_user.id
    orders = await db.get_user_orders(user_id)
    
    if not orders:
        await callback.message.answer("У вас пока нет заказов для отмены.")
        await callback.answer()
        return
    
    # Фильтруем только оплаченные заказы (их можно отменять с возвратом)
    cancellable_orders = [o for o in orders if o.get("status") == "paid"]
    
    if not cancellable_orders:
        await callback.message.answer(
            "У вас нет оплаченных заказов, которые можно отменить.\n"
            "Неоплаченные заказы автоматически отменяются через 24 часа."
        )
        await callback.answer()
        return
    
    text = "Понимаем — иногда планы меняются.\n\nВыберите заказ, который хотите отменить:\n\n"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    
    for order in cancellable_orders:
        order_number = order.get("order_number", "N/A")
        bouquets_text = ", ".join([
            f"№{b['variant']} «{b['variant_name']}» - {b['quantity']} шт."
            for b in order.get("bouquets", [])[:1]  # Показываем только первый букет для краткости
        ])
        if len(order.get("bouquets", [])) > 1:
            bouquets_text += f" и еще {len(order.get('bouquets', [])) - 1}"
        
        text += (
            f"🔸 Заказ №{order_number}\n"
            f"   Букет: {bouquets_text}\n"
            f"   Самовывоз: {order.get('pickup_date', 'N/A')} в {order.get('pickup_time', 'N/A')}\n"
            f"   Сумма: {order.get('total_price', 0):,} ₽\n\n"
        )
        
        buttons.append([
            InlineKeyboardButton(
                text=f"❌ Отменить заказ №{order_number}",
                callback_data=f"cancel_order_{order_number}"
            )
        ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_order_"))
async def order_selected_for_cancellation(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора заказа для отмены"""
    order_number = callback.data.replace("cancel_order_", "")
    
    order = await db.get_order(order_number)
    if not order:
        await callback.message.answer(
            f"Заказ №{order_number} не найден."
        )
        await callback.answer()
        return
    
    # Проверка, что заказ принадлежит пользователю
    if order.get("user_id") != callback.from_user.id:
        await callback.message.answer("Этот заказ не принадлежит вам.")
        await callback.answer()
        return
    
    await state.update_data(order_number=order_number)
    
    # Проверка времени до самовывоза
    pickup_date_str = order.get("pickup_date", "")
    pickup_time_str = order.get("pickup_time", "")
    
    # Парсинг даты
    from utils import parse_date_string
    
    now = datetime.now()
    pickup_datetime = None
    
    pickup_date_obj = parse_date_string(pickup_date_str)
    if pickup_date_obj:
        hour = int(pickup_time_str.split(":")[0])
        pickup_datetime = pickup_date_obj.replace(hour=hour, minute=0)
    
    can_cancel = True
    if pickup_datetime:
        time_diff = pickup_datetime - now
        if time_diff < timedelta(hours=48):
            can_cancel = False
    
    # Формирование текста с информацией о заказе
    bouquets_text = ", ".join([
        f"№{b['variant']} «{b['variant_name']}» - {b['quantity']} шт. - {b['count']} {'букет' if b['count'] == 1 else 'букета' if b['count'] in [2, 3, 4] else 'букетов'}"
        for b in order.get("bouquets", [])
    ])
    
    status_emoji = "✅" if order.get("status") == "paid" else "⏳"
    
    order_info_text = (
        f"Нашли ваш заказ:\n\n"
        f"🔸 Номер: {order_number}\n"
        f"🔸 Букет: {bouquets_text}\n"
        f"🔸 Самовывоз: {pickup_date_str} в {pickup_time_str}\n"
        f"🔸 Статус: {status_emoji} {'Оплачен' if order.get('status') == 'paid' else 'Ожидает оплаты'}\n\n"
    )
    
    if not can_cancel:
        await state.clear()
        await callback.message.answer(
            order_info_text +
            "⚠️ К сожалению, до самовывоза осталось менее 48 часов, и букет уже подготовлен к сборке.\n"
            "Согласно условиям, возврат в этом случае невозможен.\n\n"
            "Но! Вы можете:\n"
            "— Передумать и забрать букет (он будет ждать вас!)\n"
            "— Подарить его кому-то другому — просто сообщите новому получателю ваш номер заказа\n"
            f"— В ином случае вы можете связаться с администратором по номеру {Config.PAYMENT_PHONE}"
        )
        await callback.answer()
        return
    
    if order.get("status") != "paid":
        await state.clear()
        await callback.message.answer(
            order_info_text +
            "Этот заказ еще не оплачен. Если вы не хотите его оплачивать, "
            "он будет автоматически отменен через 24 часа после создания."
        )
        await callback.answer()
        return
    
    await state.set_state(CancellationStates.confirming_cancellation)
    
    confirmation_text = (
        order_info_text +
        "Вы хотите отменить заказ и получить возврат средств?\n\n"
        "⚠️ Обратите внимание:\n"
        "— Возврат возможен, если до самовывоза осталось более 48 часов.\n"
        "— Средства возвращаются на реквизиты, которые вы укажете далее в сообщении\n\n"
        "Подтвердите отмену:"
    )
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, отменяю заказ и прошу возврат", callback_data="confirm_cancel")],
        [InlineKeyboardButton(text="❌ Нет, всё-таки заберу букет", callback_data="cancel_cancel")]
    ])
    
    await callback.message.answer(confirmation_text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "confirm_cancel", CancellationStates.confirming_cancellation)
async def cancellation_confirmed(callback: CallbackQuery, state: FSMContext):
    """Подтверждение отмены заказа"""
    data = await state.get_data()
    order_number = data.get("order_number")
    
    await state.set_state(CancellationStates.entering_refund_card)
    
    await callback.message.answer(
        f"Принято. Ваш заказ №{order_number} отменён.\n\n"
        "Напишите пожалуйста Ваш номер карты, для того чтобы мы вернули вам деньги"
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_cancel")
async def cancellation_cancelled(callback: CallbackQuery, state: FSMContext):
    """Отмена процесса отмены заказа"""
    await state.clear()
    await callback.message.answer("Хорошо, заказ остается активным. Ждем вас на самовывозе! 💐")
    await callback.answer()


@router.message(CancellationStates.entering_refund_card, F.text)
async def refund_card_entered(message: Message, state: FSMContext):
    """Обработка ввода номера карты для возврата"""
    card_number = message.text.strip()
    data = await state.get_data()
    order_number = data.get("order_number")
    
    # Получаем заказ перед обновлением
    order = await db.get_order(order_number)
    
    # Обновление статуса заказа
    await db.update_order_status(order_number, "cancelled", refund_card=card_number)
    
    # Обновление в Google Sheets
    refund_amount = order.get('total_price', 0) if order else 0
    sheets.update_order_status(order_number, "cancelled", order=order, refund_amount=refund_amount)
    
    # Уведомление администраторов
    admin_text = (
        f"📋 Заказ №{order_number} — отмена, требуется возврат средств\n\n"
        f"Номер карты: {card_number}\n"
        f"Сумма возврата: {order.get('total_price', 0):,} ₽\n"
        f"ФИО: {order.get('last_name', '')} {order.get('first_name', '')}"
    )
    
    for admin_id in Config.ADMIN_IDS:
        try:
            await message.bot.send_message(admin_id, admin_text)
        except Exception as e:
            print(f"Error sending cancellation notice to admin {admin_id}: {e}")
    
    await message.answer(
        "Номер карты принят, средства вернутся в течение 24 часов"
    )
    
    await state.clear()

