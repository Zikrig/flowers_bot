import logging
import asyncio
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from config import Config
from database import Database
from google_sheets import GoogleSheets, _dbg_log
from order_template import OrderTemplate
from handlers.order import OrderStates

logger = logging.getLogger(__name__)

router = Router()
db = Database()
sheets = GoogleSheets()
order_template = OrderTemplate()

# Блокировки для предотвращения одновременной обработки одного заказа
_order_locks: dict[str, asyncio.Lock] = {}

def _get_order_lock(order_number: str) -> asyncio.Lock:
    """Получить блокировку для заказа"""
    if order_number not in _order_locks:
        _order_locks[order_number] = asyncio.Lock()
    return _order_locks[order_number]


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
    
    # Проверяем наличие админов
    if not Config.ADMIN_IDS:
        logger.error("ADMIN_IDS пустой! Сообщения админам не будут отправлены.")
        await message.answer("⚠️ Ошибка: администраторы не настроены. Обратитесь к разработчику.")
    else:
        logger.info(f"Отправка сообщений {len(Config.ADMIN_IDS)} админам: {Config.ADMIN_IDS}")
    
    sent_count = 0
    for admin_id in Config.ADMIN_IDS:
        try:
            logger.info(f"Попытка отправить сообщение админу {admin_id}")
            
            if file_type == "photo":
                sent_msg = await message.bot.send_photo(
                    admin_id,
                    photo=file_id,
                    caption=admin_text
                )
                logger.info(f"Фото отправлено админу {admin_id}, message_id={sent_msg.message_id}")
            else:
                sent_msg = await message.bot.send_document(
                    admin_id,
                    document=file_id,
                    caption=admin_text
                )
                logger.info(f"Документ отправлен админу {admin_id}, message_id={sent_msg.message_id}")
            
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
            keyboard_msg = await message.bot.send_message(
                admin_id,
                f"Заказ №{order_number}",
                reply_markup=admin_keyboard
            )
            logger.info(f"Кнопки отправлены админу {admin_id}, message_id={keyboard_msg.message_id}")
            sent_count += 1
            
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения админу {admin_id}: {e}", exc_info=True)
    
    if sent_count == 0:
        logger.error(f"Не удалось отправить сообщения ни одному админу из {len(Config.ADMIN_IDS)}")
    else:
        logger.info(f"Сообщения успешно отправлены {sent_count} из {len(Config.ADMIN_IDS)} админов")
    
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
    admin_id = callback.from_user.id
    admin_name = f"@{callback.from_user.username}" if callback.from_user.username else str(admin_id)
    
    logger.info(f"Админ {admin_name} ({admin_id}) пытается подтвердить заказ {order_number}")
    
    # Проверка прав администратора
    if admin_id not in Config.ADMIN_IDS:
        logger.warning(f"Пользователь {admin_id} не является админом")
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    # Используем блокировку для предотвращения одновременной обработки
    async with _get_order_lock(order_number):
        order = await db.get_order(order_number)
        if not order:
            logger.error(f"Заказ {order_number} не найден")
            await callback.answer("Заказ не найден", show_alert=True)
            return
        
        # Проверяем, не подтвержден ли уже заказ
        current_status = order.get("status")
        if current_status == "paid":
            logger.info(f"Заказ {order_number} уже подтвержден ранее (статус: {current_status})")
            await callback.answer("Оплата уже подтверждена другим администратором", show_alert=True)
            try:
                await callback.message.edit_text(
                    f"✅ Оплата по заказу №{order_number} уже подтверждена ранее."
                )
            except Exception as e:
                logger.warning(f"Не удалось обновить сообщение: {e}")
            return
        
        logger.info(f"Подтверждение заказа {order_number} админом {admin_name}")
        
        # Обновление статуса заказа
        await db.update_order_status(
            order_number, 
            "paid",
            payment_confirmed_by=admin_id,
            payment_confirmed_at=datetime.now().isoformat()
        )
        order["status"] = "paid"
        
        # Добавление в Google Sheets
        order["order_number"] = order_number
        try:
            sheets.add_order(order)
            logger.info(f"Заказ {order_number} добавлен в Google Sheets")
        except Exception as e:
            logger.error(f"Ошибка при добавлении заказа в Google Sheets: {e}", exc_info=True)
        
        # Создание бланка заказа
        try:
            blank_path = order_template.create_order_blank(order)
            logger.info(f"Бланк заказа создан: {blank_path}")
        except Exception as e:
            logger.error(f"Ошибка при создании бланка заказа: {e}", exc_info=True)
    
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
        f"Для получения необходимо назвать номер Вашего заказа. \n"
        f"Хотите сделать еще заказ? Нажмите /start"
    )
    
    try:
        await callback.bot.send_message(user_id, confirmation_text)
        logger.info(f"Подтверждение отправлено пользователю {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке подтверждения пользователю {user_id}: {e}", exc_info=True)
    
    # Уведомляем всех админов о подтверждении
    for other_admin_id in Config.ADMIN_IDS:
        if other_admin_id != admin_id:
            try:
                await callback.bot.send_message(
                    other_admin_id,
                    f"✅ Оплата по заказу №{order_number} подтверждена админом {admin_name}."
                )
            except Exception as e:
                logger.warning(f"Не удалось уведомить админа {other_admin_id}: {e}")
    
    await callback.answer("Оплата подтверждена", show_alert=True)
    try:
        await callback.message.edit_text(
            f"✅ Оплата по заказу №{order_number} подтверждена.\n"
            f"Пользователю отправлено уведомление."
        )
    except Exception as e:
        logger.warning(f"Не удалось обновить сообщение: {e}")


@router.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject_payment(callback: CallbackQuery):
    """Отклонение оплаты администратором"""
    order_number = callback.data.replace("admin_reject_", "")
    admin_id = callback.from_user.id
    admin_name = f"@{callback.from_user.username}" if callback.from_user.username else str(admin_id)
    
    logger.info(f"Админ {admin_name} ({admin_id}) пытается отклонить заказ {order_number}")
    
    if admin_id not in Config.ADMIN_IDS:
        logger.warning(f"Пользователь {admin_id} не является админом")
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    # Используем блокировку для предотвращения одновременной обработки
    async with _get_order_lock(order_number):
        order = await db.get_order(order_number)
        if not order:
            logger.error(f"Заказ {order_number} не найден")
            await callback.answer("Заказ не найден", show_alert=True)
            return
        
        # Если уже подтвержден, отклонять нельзя
        if order.get("status") == "paid":
            logger.info(f"Попытка отклонить уже подтвержденный заказ {order_number}")
            await callback.answer("Оплата уже подтверждена другим администратором", show_alert=True)
            try:
                await callback.message.edit_text(
                    f"✅ Оплата по заказу №{order_number} уже подтверждена ранее."
                )
            except Exception as e:
                logger.warning(f"Не удалось обновить сообщение: {e}")
            return
        
        # Обновляем статус
        await db.update_order_status(
            order_number,
            "payment_rejected",
            payment_rejected_by=admin_id,
            payment_rejected_at=datetime.now().isoformat()
        )
        logger.info(f"Заказ {order_number} отклонен админом {admin_name}")
    
    user_id = order.get("user_id")
    rejection_text = (
        f"❌ К сожалению, оплата по заказу №{order_number} не подтверждена.\n"
        f"Пожалуйста, проверьте правильность реквизитов и попробуйте снова.\n"
        f"Если у вас есть вопросы, свяжитесь с нами: {', '.join(Config.ADMIN_CONTACTS)}"
    )
    
    try:
        await callback.bot.send_message(user_id, rejection_text)
        logger.info(f"Уведомление об отклонении отправлено пользователю {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}", exc_info=True)
    
    # Уведомляем всех админов об отклонении
    for other_admin_id in Config.ADMIN_IDS:
        if other_admin_id != admin_id:
            try:
                await callback.bot.send_message(
                    other_admin_id,
                    f"❌ Оплата по заказу №{order_number} отклонена админом {admin_name}."
                )
            except Exception as e:
                logger.warning(f"Не удалось уведомить админа {other_admin_id}: {e}")
    
    await callback.answer("Оплата отклонена", show_alert=True)
    try:
        await callback.message.edit_text(
            f"❌ Оплата по заказу №{order_number} отклонена.\n"
            f"Пользователю отправлено уведомление."
        )
    except Exception as e:
        logger.warning(f"Не удалось обновить сообщение: {e}")
