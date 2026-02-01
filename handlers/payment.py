from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from config import Config
from database import Database
from google_sheets import GoogleSheets
from order_template import OrderTemplate
from handlers.order import OrderStates

router = Router()
db = Database()
sheets = GoogleSheets()
order_template = OrderTemplate()


@router.callback_query(F.data == "send_receipt", StateFilter(OrderStates.waiting_payment))
async def send_receipt_button(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки 'Отправить чек'"""
    await state.set_state(OrderStates.waiting_receipt)
    
    await callback.message.answer(
        "📎 Отправьте фотографию или файл с квитанцией об оплате.\n"
        "Максимальный размер файла: 20 МБ"
    )
    await callback.answer()


@router.message(StateFilter(OrderStates.waiting_receipt), F.photo | F.document)
async def receipt_received(message: Message, state: FSMContext):
    """Обработка получения чека (фото или файл)"""
    data = await state.get_data()
    order_number = data.get("order_number")
    
    if not order_number:
        await message.answer("Ошибка: номер заказа не найден.")
        await state.set_state(OrderStates.waiting_payment)
        return
    
    order = await db.get_order(order_number)
    if not order:
        await message.answer("Ошибка: заказ не найден.")
        await state.set_state(OrderStates.waiting_payment)
        return
    
    # Проверка размера файла (20 МБ = 20 * 1024 * 1024 байт)
    MAX_FILE_SIZE = 20 * 1024 * 1024
    
    file_id = None
    file_type = None
    
    if message.photo:
        # Обработка фото
        photo = message.photo[-1]  # Берем фото наибольшего размера
        file_id = photo.file_id
        file_type = "photo"
        
        # Проверяем размер фото
        file_info = await message.bot.get_file(file_id)
        if file_info.file_size and file_info.file_size > MAX_FILE_SIZE:
            await message.answer(
                f"❌ Файл слишком большой ({file_info.file_size / 1024 / 1024:.1f} МБ). "
                "Максимальный размер: 20 МБ"
            )
            return
    
    elif message.document:
        # Обработка документа
        document = message.document
        file_id = document.file_id
        file_type = "document"
        
        # Проверяем размер файла
        if document.file_size and document.file_size > MAX_FILE_SIZE:
            await message.answer(
                f"❌ Файл слишком большой ({document.file_size / 1024 / 1024:.1f} МБ). "
                "Максимальный размер: 20 МБ"
            )
            return
    
    if not file_id:
        await message.answer("Пожалуйста, отправьте фотографию или файл с квитанцией.")
        return
    
    # Сохраняем file_id чека в заказе
    await db.update_order_status(order_number, "pending_payment", receipt_file_id=file_id, receipt_file_type=file_type)
    
    # Формируем текст о букетах отдельно
    bouquets_list = []
    for b in order.get('bouquets', []):
        count = b['count']
        if count == 1:
            count_text = 'букет'
        elif count in [2, 3, 4]:
            count_text = 'букета'
        else:
            count_text = 'букетов'
        bouquets_list.append(f"№{b['variant']} «{b['variant_name']}» - {b['quantity']} шт. - {count} {count_text}")
    bouquets_str = ', '.join(bouquets_list)
    
    # Отправляем администраторам
    admin_text = (
        f"📋 Новый заказ требует подтверждения оплаты:\n\n"
        f"🔹 Номер заказа: {order_number}\n"
        f"🔹 ФИО: {order.get('last_name', '')} {order.get('first_name', '')}\n"
        f"🔹 Ник: @{order.get('username', 'N/A')}\n"
        f"🔹 Сумма: {order.get('total_price', 0):,} ₽\n"
        f"🔹 Букеты: {bouquets_str}\n"
        f"🔹 Самовывоз: {order.get('pickup_date')} в {order.get('pickup_time')}\n\n"
        f"Проверьте оплату и подтвердите её."
    )
    
    for admin_id in Config.ADMIN_IDS:
        try:
            if file_type == "photo":
                await message.bot.send_photo(
                    admin_id,
                    photo=file_id,
                    caption=admin_text
                )
            else:
                await message.bot.send_document(
                    admin_id,
                    document=file_id,
                    caption=admin_text
                )
            
            # Кнопки для администратора
            admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Подтвердить оплату",
                        callback_data=f"admin_confirm_{order_number}"
                    ),
                    InlineKeyboardButton(
                        text="❌ Отклонить",
                        callback_data=f"admin_reject_{order_number}"
                    )
                ]
            ])
            await message.bot.send_message(
                admin_id,
                f"Заказ №{order_number}",
                reply_markup=admin_keyboard
            )
        except Exception as e:
            print(f"Error sending to admin {admin_id}: {e}")
    
    await message.answer(
        "✅ Чек получен! Мы проверим поступление средств и подтвердим оплату."
    )
    
    # Возвращаемся в состояние ожидания оплаты
    await state.set_state(OrderStates.waiting_payment)


@router.message(StateFilter(OrderStates.waiting_receipt))
async def invalid_receipt_format(message: Message):
    """Обработка некорректного формата чека"""
    await message.answer(
        "Пожалуйста, отправьте фотографию или файл с квитанцией об оплате.\n"
        "Максимальный размер файла: 20 МБ"
    )


@router.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm_payment(callback: CallbackQuery):
    """Подтверждение оплаты администратором"""
    order_number = callback.data.replace("admin_confirm_", "")
    
    # Проверка прав администратора
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    order = await db.get_order(order_number)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    
    # Обновление статуса заказа
    await db.update_order_status(order_number, "paid")
    
    # Добавление в Google Sheets
    order["order_number"] = order_number
    sheets.add_order(order)
    
    # Создание бланка заказа
    order["order_number"] = order_number
    blank_path = order_template.create_order_blank(order)
    
    # Формируем текст о букетах для пользователя
    bouquets_list_user = []
    for b in order.get('bouquets', []):
        count = b['count']
        if count == 1:
            count_text = 'букет'
        elif count in [2, 3, 4]:
            count_text = 'букета'
        else:
            count_text = 'букетов'
        bouquets_list_user.append(f"№{b['variant']} «{b['variant_name']}» - {b['quantity']} шт. - {count} {count_text}")
    bouquets_str_user = ', '.join(bouquets_list_user)
    
    # Отправка подтверждения пользователю
    user_id = order.get("user_id")
    confirmation_text = (
        f"✅ Оплата получена!\n\n"
        f"Вот детали твоего заказа:\n\n"
        f"🔹 Номер заказа: {order_number}\n"
        f"🔹 Букет: {bouquets_str_user}\n"
        f"🔹 Самовывоз: {order.get('pickup_date')} в {order.get('pickup_time')}\n"
        f"🔹 Адрес: {Config.PICKUP_ADDRESS}\n"
        f"🔹 Получатель: {order.get('last_name', '')} {order.get('first_name', '')}\n\n"
        f"💐 Букет уже готовят! Он будет упакован и бережно сохранен! "
        f"Для получения необходимо назвать номер Вашего заказа."
    )
    
    try:
        await callback.bot.send_message(user_id, confirmation_text)
    except Exception as e:
        print(f"Error sending confirmation to user {user_id}: {e}")
    
    await callback.answer("Оплата подтверждена", show_alert=True)
    await callback.message.edit_text(
        f"✅ Оплата по заказу №{order_number} подтверждена.\n"
        f"Пользователю отправлено уведомление."
    )


@router.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject_payment(callback: CallbackQuery):
    """Отклонение оплаты администратором"""
    order_number = callback.data.replace("admin_reject_", "")
    
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    order = await db.get_order(order_number)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    
    user_id = order.get("user_id")
    rejection_text = (
        f"❌ К сожалению, оплата по заказу №{order_number} не подтверждена.\n"
        f"Пожалуйста, проверьте правильность реквизитов и попробуйте снова.\n"
        f"Если у вас есть вопросы, свяжитесь с нами: {', '.join(Config.ADMIN_CONTACTS)}"
    )
    
    try:
        await callback.bot.send_message(user_id, rejection_text)
    except Exception as e:
        print(f"Error sending rejection to user {user_id}: {e}")
    
    await callback.answer("Оплата отклонена", show_alert=True)
    await callback.message.edit_text(
        f"❌ Оплата по заказу №{order_number} отклонена.\n"
        f"Пользователю отправлено уведомление."
    )
