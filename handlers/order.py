from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import List, Dict
from config import Config
from database import Database
from google_sheets import GoogleSheets
from order_template import OrderTemplate
from datetime import datetime, timedelta
import os

router = Router()
db = Database()
sheets = GoogleSheets()
order_template = OrderTemplate()


class OrderStates(StatesGroup):
    """Состояния FSM для оформления заказа"""
    waiting_consent = State()  # Ожидание согласия на обработку персональных данных
    selecting_bouquet = State()  # Выбор варианта букета
    selecting_quantity = State()  # Выбор количества тюльпанов
    selecting_more_bouquets = State()  # Выбор дополнительных букетов
    selecting_date = State()  # Выбор даты самовывоза
    selecting_time = State()  # Выбор времени самовывоза
    entering_name = State()  # Ввод имени и фамилии
    confirming_order = State()  # Подтверждение заказа
    waiting_payment = State()  # Ожидание оплаты
    waiting_receipt = State()  # Ожидание отправки чека через кнопку
    entering_refund_card = State()  # Ввод номера карты для возврата


async def show_bouquet_selection(message_or_callback, state: FSMContext):
    """Показать варианты букетов"""
    # Получаем user_id из message или callback
    if hasattr(message_or_callback, 'from_user'):
        user_id = message_or_callback.from_user.id
    elif hasattr(message_or_callback, 'message'):
        user_id = message_or_callback.message.from_user.id
    else:
        user_id = None
    
    if not user_id:
        # Пробуем получить из chat
        if hasattr(message_or_callback, 'chat'):
            user_id = message_or_callback.chat.id
        elif hasattr(message_or_callback, 'message') and hasattr(message_or_callback.message, 'chat'):
            user_id = message_or_callback.message.chat.id
        else:
            # Если это callback, пробуем через message
            if hasattr(message_or_callback, 'message'):
                await message_or_callback.message.answer("Ошибка: не удалось определить пользователя.")
            return
    
    # Проверяем, есть ли у пользователя согласие
    user = await db.get_user(user_id)
    if user and user.get("consent_given"):
        # У пользователя уже есть согласие, сразу показываем букеты
        await show_bouquet_options(message_or_callback, state)
    else:
        # Нужно получить согласие
        await state.set_state(OrderStates.waiting_consent)
        
        consent_text = (
            "📋 Перед началом оформления заказа необходимо дать согласие на обработку персональных данных.\n\n"
            "Согласие на обработку персональных данных:\n"
            "Я даю согласие на обработку моих персональных данных (ФИО, контактные данные) "
            "в целях оформления и выполнения заказа, а также для связи со мной по вопросам заказа.\n\n"
            "Согласны ли вы на обработку персональных данных?"
        )
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, согласен", callback_data="consent_yes")],
            [InlineKeyboardButton(text="❌ Нет", callback_data="consent_no")]
        ])
        
        # Определяем, как отправить сообщение
        # Если это Message объект
        if hasattr(message_or_callback, 'answer') and hasattr(message_or_callback, 'from_user'):
            await message_or_callback.answer(consent_text, reply_markup=keyboard)
        # Если это CallbackQuery объект
        elif hasattr(message_or_callback, 'message'):
            await message_or_callback.message.answer(consent_text, reply_markup=keyboard)
        else:
            # Fallback
            await message_or_callback.answer(consent_text, reply_markup=keyboard)


async def show_bouquet_options(message_or_callback, state: FSMContext):
    """Показать варианты букетов с кнопками"""
    await state.set_state(OrderStates.selecting_bouquet)
    
    # Отправляем картинку с цветами, если она существует
    colors_photo_path = "data/colors.jpg"
    if os.path.exists(colors_photo_path):
        try:
            if hasattr(message_or_callback, 'message'):
                await message_or_callback.message.answer_photo(photo=FSInputFile(colors_photo_path))
            else:
                await message_or_callback.answer_photo(photo=FSInputFile(colors_photo_path))
        except Exception as e:
            print(f"Error sending colors photo: {e}")
    
    text = (
        "Отлично! Вот все 6 вариантов:\n\n"
        "Выберите вариант букета:"
    )
    
    # Отправка фотографий букетов
    try:
        from aiogram.types import InputMediaPhoto
        media_group = []
        for i in range(1, 7):
            photo_path = Config.BOUQUET_VARIANTS[i]["photo"]
            if os.path.exists(photo_path):
                media_group.append(InputMediaPhoto(media=FSInputFile(photo_path)))
        
        if media_group:
            if hasattr(message_or_callback, 'message'):
                await message_or_callback.message.answer_media_group(media_group)
            else:
                await message_or_callback.answer_media_group(media_group)
    except Exception as e:
        print(f"Error sending photos: {e}")
    
    # Кнопки для выбора букета
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1️⃣ Микс", callback_data="bouquet_1"),
            InlineKeyboardButton(text="2️⃣ Красный", callback_data="bouquet_2")
        ],
        [
            InlineKeyboardButton(text="3️⃣ Жёлтый", callback_data="bouquet_3"),
            InlineKeyboardButton(text="4️⃣ Белый", callback_data="bouquet_4")
        ],
        [
            InlineKeyboardButton(text="5️⃣ Ж+Ф", callback_data="bouquet_5"),
            InlineKeyboardButton(text="6️⃣ К+Ж", callback_data="bouquet_6")
        ]
    ])
    
    if hasattr(message_or_callback, 'message'):
        await message_or_callback.message.answer(text, reply_markup=keyboard)
    else:
        await message_or_callback.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "consent_yes", StateFilter(OrderStates.waiting_consent))
async def consent_given(callback: CallbackQuery, state: FSMContext):
    """Согласие получено, сохраняем и показываем варианты букетов"""
    # Сохраняем согласие
    await db.update_user_consent(callback.from_user.id, True)
    
    # Показываем варианты букетов
    await show_bouquet_options(callback, state)
    await callback.answer()


@router.callback_query(F.data == "consent_no")
async def consent_denied(callback: CallbackQuery):
    """Отказ от согласия"""
    await callback.message.answer(
        "Для оформления заказа необходимо дать согласие на обработку персональных данных. "
        "Если вы передумаете, нажмите /start"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bouquet_"), StateFilter(OrderStates.selecting_bouquet))
async def bouquet_selected(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора букета через кнопку"""
    variant_num = int(callback.data.replace("bouquet_", ""))
    variant = Config.BOUQUET_VARIANTS[variant_num]
    
    await state.update_data(
        current_bouquet_variant=variant_num,
        current_bouquet_name=variant["name"]
    )
    await state.set_state(OrderStates.selecting_quantity)
    
    # Отправка фотографий количества тюльпанов
    try:
        from aiogram.types import InputMediaPhoto
        media_group = []
        
        photo_15_path = "data/15.jpg"
        photo_25_path = "data/25.jpg"
        
        if os.path.exists(photo_15_path):
            media_group.append(InputMediaPhoto(media=FSInputFile(photo_15_path)))
        if os.path.exists(photo_25_path):
            media_group.append(InputMediaPhoto(media=FSInputFile(photo_25_path)))
        
        if media_group:
            await callback.message.answer_media_group(media_group)
    except Exception as e:
        print(f"Error sending quantity photos: {e}")
    
    text = (
        f"Вы выбрали букет №{variant_num} — «{variant['name']}»\n\n"
        "Выберете количество:\n"
        f"Если вам нужно другое количество – напишите в личные сообщения {', '.join(Config.ADMIN_CONTACTS)}"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="15 штук", callback_data="qty_15")],
        [InlineKeyboardButton(text="25 штук", callback_data="qty_25")]
    ])
    
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.in_(["qty_15", "qty_25"]), StateFilter(OrderStates.selecting_quantity))
async def quantity_selected(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора количества"""
    quantity = int(callback.data.split("_")[1])
    data = await state.get_data()
    
    variant_num = data.get("current_bouquet_variant")
    variant_name = data.get("current_bouquet_name")
    
    # Проверяем, есть ли уже такой букет в списке
    bouquets = data.get("bouquets", [])
    found = False
    for bouquet in bouquets:
        if bouquet["variant"] == variant_num and bouquet["quantity"] == quantity:
            bouquet["count"] += 1
            found = True
            break
    
    if not found:
        bouquets.append({
            "variant": variant_num,
            "variant_name": variant_name,
            "quantity": quantity,
            "count": 1
        })
    
    await state.update_data(bouquets=bouquets)
    await state.set_state(OrderStates.selecting_more_bouquets)
    
    text = "Хотите выбрать еще букеты?"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="more_yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="more_no")]
    ])
    
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "more_yes", StateFilter(OrderStates.selecting_more_bouquets))
async def select_more_bouquets(callback: CallbackQuery, state: FSMContext):
    """Выбор дополнительных букетов"""
    await state.set_state(OrderStates.selecting_bouquet)
    
    # Используем ту же функцию показа букетов с кнопками
    await show_bouquet_options(callback, state)
    await callback.answer()


@router.callback_query(F.data == "more_no", StateFilter(OrderStates.selecting_more_bouquets))
async def no_more_bouquets(callback: CallbackQuery, state: FSMContext):
    """Переход к выбору даты"""
    await state.set_state(OrderStates.selecting_date)
    
    schedule = Config.get_pickup_schedule()
    
    text = "Теперь выберите, когда заберете букет:\n\n"
    buttons = []
    
    for date_str, times in schedule.items():
        start_hour = times["start"]
        end_hour = times["end"]
        text += f"{date_str} – с {start_hour}:00 до {end_hour}:00\n"
        buttons.append([InlineKeyboardButton(
            text=date_str,
            callback_data=f"date_{date_str}"
        )])
    
    text += "\nВыберите дату:"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("date_"), StateFilter(OrderStates.selecting_date))
async def date_selected(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора даты"""
    date_str = callback.data.replace("date_", "")
    schedule = Config.get_pickup_schedule()
    date_schedule = schedule.get(date_str)
    
    if not date_schedule:
        await callback.answer("Неверная дата")
        return
    
    await state.update_data(pickup_date=date_str)
    await state.set_state(OrderStates.selecting_time)
    
    start_hour = date_schedule["start"]
    end_hour = date_schedule["end"]
    
    # Формируем кнопки для времени
    time_buttons = []
    row = []
    for hour in range(start_hour, end_hour + 1):
        time_str = f"{hour:02d}:00"
        row.append(InlineKeyboardButton(text=time_str, callback_data=f"time_{time_str}"))
        if len(row) == 2:
            time_buttons.append(row)
            row = []
    if row:
        time_buttons.append(row)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=time_buttons)
    
    await callback.message.answer("Выберите время:", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("time_"), StateFilter(OrderStates.selecting_time))
async def time_selected(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора времени"""
    time_str = callback.data.replace("time_", "")
    
    await state.update_data(pickup_time=time_str)
    await state.set_state(OrderStates.entering_name)
    
    # Получаем данные пользователя
    user = await db.get_user(callback.from_user.id)
    user_first_name = callback.from_user.first_name or ""
    user_last_name = callback.from_user.last_name or ""
    
    # Если есть сохраненные данные или имя из Telegram
    if user and user.get("first_name") and user.get("last_name"):
        first_name = user.get("first_name")
        last_name = user.get("last_name")
    elif user_first_name and user_last_name:
        first_name = user_first_name
        last_name = user_last_name
    else:
        # Предлагаем использовать имя из профиля или ввести вручную
        text = (
            "Отлично! Осталось совсем немного.\n"
            "Выберите способ указания имени:"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"Использовать имя из профиля: {user_first_name} {user_last_name}" if user_first_name else "Использовать имя из профиля",
                callback_data="use_profile_name"
            )],
            [InlineKeyboardButton(text="Ввести имя вручную", callback_data="enter_name_manually")]
        ])
        
        await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        return
    
    # Используем сохраненное или имя из профиля
    await state.update_data(
        first_name=first_name,
        last_name=last_name,
        username=callback.from_user.username or ""
    )
    
    # Сохраняем имя пользователя
    await db.save_user(callback.from_user.id, {
        "first_name": first_name,
        "last_name": last_name,
        "username": callback.from_user.username or ""
    })
    
    # Переходим к подтверждению заказа
    await process_order_confirmation(callback, state)


@router.callback_query(F.data == "use_profile_name", StateFilter(OrderStates.entering_name))
async def use_profile_name(callback: CallbackQuery, state: FSMContext):
    """Использовать имя из профиля Telegram"""
    first_name = callback.from_user.first_name or "Имя"
    last_name = callback.from_user.last_name or "Фамилия"
    
    await state.update_data(
        first_name=first_name,
        last_name=last_name,
        username=callback.from_user.username or ""
    )
    
    # Сохраняем имя пользователя
    await db.save_user(callback.from_user.id, {
        "first_name": first_name,
        "last_name": last_name,
        "username": callback.from_user.username or ""
    })
    
    await process_order_confirmation(callback, state)
    await callback.answer()


@router.callback_query(F.data == "enter_name_manually", StateFilter(OrderStates.entering_name))
async def enter_name_manually(callback: CallbackQuery, state: FSMContext):
    """Запрос на ввод имени вручную"""
    await callback.message.answer(
        "Пожалуйста, отправьте ваше Имя и Фамилию через пробел.\n"
        "Например: Иван Иванов"
    )
    await callback.answer()


@router.message(StateFilter(OrderStates.entering_name), F.text)
async def name_entered(message: Message, state: FSMContext):
    """Обработка ввода имени вручную"""
    name_parts = message.text.strip().split(maxsplit=1)
    if len(name_parts) < 2:
        await message.answer("Пожалуйста, укажите Имя и Фамилию через пробел.")
        return
    
    first_name = name_parts[0]
    last_name = name_parts[1]
    
    await state.update_data(
        first_name=first_name,
        last_name=last_name,
        username=message.from_user.username or ""
    )
    
    # Сохраняем имя пользователя
    await db.save_user(message.from_user.id, {
        "first_name": first_name,
        "last_name": last_name,
        "username": message.from_user.username or ""
    })
    
    # Переходим к подтверждению заказа
    await process_order_confirmation_from_message(message, state)


async def process_order_confirmation(callback: CallbackQuery, state: FSMContext):
    """Обработка подтверждения заказа из callback"""
    data = await state.get_data()
    bouquets = data.get("bouquets", [])
    total_price = 0
    
    for bouquet in bouquets:
        quantity = bouquet["quantity"]
        count = bouquet["count"]
        price = Config.PRICE_15 if quantity == 15 else Config.PRICE_25
        total_price += price * count
    
    await state.update_data(total_price=total_price)
    
    # Формируем текст подтверждения
    bouquets_text = []
    for bouquet in bouquets:
        count = bouquet['count']
        if count == 1:
            count_text = "1 букет"
        elif count in [2, 3, 4]:
            count_text = f"{count} букета"
        else:
            count_text = f"{count} букетов"
        
        bouquets_text.append(
            f"№{bouquet['variant']} «{bouquet['variant_name']}» - "
            f"{bouquet['quantity']} шт. – {count_text}"
        )
    
    confirmation_text = (
        "Отлично! Проверьте, всё ли верно:\n\n"
        f"🔹 Букет: {', '.join(bouquets_text)}\n"
        f"🔹 Самовывоз: {data.get('pickup_date')}, с {data.get('pickup_time')} до "
        f"{int(data.get('pickup_time', '00:00').split(':')[0]) + 1:02d}:00\n"
        f"🔹 Стоимость: {total_price:,} ₽\n"
        f"🔹 Получатель: {data.get('last_name', '')} {data.get('first_name', '')}\n\n"
        "Всё правильно?"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, всё верно — подтверждаю", callback_data="confirm_order")],
        [InlineKeyboardButton(text="🔄 Нет, хочу изменить", callback_data="change_order")]
    ])
    
    await callback.message.answer(confirmation_text, reply_markup=keyboard)


async def process_order_confirmation_from_message(message: Message, state: FSMContext):
    """Обработка подтверждения заказа из message"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    data = await state.get_data()
    bouquets = data.get("bouquets", [])
    total_price = 0
    
    for bouquet in bouquets:
        quantity = bouquet["quantity"]
        count = bouquet["count"]
        price = Config.PRICE_15 if quantity == 15 else Config.PRICE_25
        total_price += price * count
    
    await state.update_data(total_price=total_price)
    
    # Формируем текст подтверждения
    bouquets_text = []
    for bouquet in bouquets:
        count = bouquet['count']
        if count == 1:
            count_text = "1 букет"
        elif count in [2, 3, 4]:
            count_text = f"{count} букета"
        else:
            count_text = f"{count} букетов"
        
        bouquets_text.append(
            f"№{bouquet['variant']} «{bouquet['variant_name']}» - "
            f"{bouquet['quantity']} шт. – {count_text}"
        )
    
    confirmation_text = (
        "Отлично! Проверьте, всё ли верно:\n\n"
        f"🔹 Букет: {', '.join(bouquets_text)}\n"
        f"🔹 Самовывоз: {data.get('pickup_date')}, с {data.get('pickup_time')} до "
        f"{int(data.get('pickup_time', '00:00').split(':')[0]) + 1:02d}:00\n"
        f"🔹 Стоимость: {total_price:,} ₽\n"
        f"🔹 Получатель: {data.get('last_name', '')} {data.get('first_name', '')}\n\n"
        "Всё правильно?"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, всё верно — подтверждаю", callback_data="confirm_order")],
        [InlineKeyboardButton(text="🔄 Нет, хочу изменить", callback_data="change_order")]
    ])
    
    await message.answer(confirmation_text, reply_markup=keyboard)
    await state.set_state(OrderStates.confirming_order)


@router.callback_query(F.data == "confirm_order", StateFilter(OrderStates.confirming_order))
async def order_confirmed(callback: CallbackQuery, state: FSMContext):
    """Подтверждение заказа"""
    data = await state.get_data()
    
    # Сохранение заказа
    order_data = {
        "user_id": callback.from_user.id,
        "first_name": data.get("first_name"),
        "last_name": data.get("last_name"),
        "username": data.get("username", ""),
        "bouquets": data.get("bouquets", []),
        "pickup_date": data.get("pickup_date"),
        "pickup_time": data.get("pickup_time"),
        "total_price": data.get("total_price", 0),
        "status": "pending_payment"
    }
    
    order_number = await db.save_order(order_data)
    
    await state.update_data(order_number=order_number)
    await state.set_state(OrderStates.waiting_payment)
    
    payment_text = (
        f"Спасибо! Ваш заказ принят.\n\n"
        f"💳 Оплатите {data.get('total_price', 0):,} ₽ по реквизитам:\n"
        f"перевод СБЕРБАНК получатель {Config.PAYMENT_RECEIVER}\n"
        f"{Config.PAYMENT_PHONE}\n\n"
        "❗ Важно:\n"
        "Оплатить нужно в течение 24 часов с момента оформления заказа.\n"
        "Если оплата не поступит — заказ автоматически отменится.\n\n"
        "После оплаты нажмите кнопку «Отправить чек» и отправьте фотографию или файл с квитанцией об оплате.\n"
        "Мы проверим поступление средств и обязательно подтвердим оплату в этом чате."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 Отправить чек", callback_data="send_receipt")]
    ])
    
    await callback.message.answer(payment_text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "change_order", StateFilter(OrderStates.confirming_order))
async def change_order(callback: CallbackQuery, state: FSMContext):
    """Изменение заказа"""
    text = (
        "Что вы хотите изменить?\n\n"
        "1. Вариант букета\n"
        "2. Количество тюльпанов в букете\n"
        "3. Количество букетов\n"
        "4. Дату и время самовывоза\n\n"
        "Напишите номер пункта (1-4) или нажмите /start для начала нового заказа."
    )
    
    await callback.message.answer(text)
    await callback.answer()


@router.message(StateFilter(OrderStates.confirming_order), F.text.regexp(r'^[1-4]$'))
async def process_change_order(message: Message, state: FSMContext):
    """Обработка выбора пункта изменения заказа"""
    choice = int(message.text)
    
    if choice == 1 or choice == 2:
        # Изменение варианта или количества - начинаем заново с выбора букета
        await state.set_state(OrderStates.selecting_bouquet)
        await state.update_data(bouquets=[])
        
        text = (
            "Выберите букет заново:\n\n"
            "1️⃣. Микс\n"
            "2️⃣. Красный\n"
            "3️⃣. Жёлтый\n"
            "4️⃣. Белый\n"
            "5️⃣. Жёлтый + фиолетовый\n"
            "6️⃣. Красный + жёлтый\n\n"
            "💬 Напишите номер букета (от 1 до 6)."
        )
        await message.answer(text)
    
    elif choice == 3:
        # Изменение количества букетов - пока не реализовано, предлагаем начать заново
        await message.answer(
            "Для изменения количества букетов начните оформление заказа заново. "
            "Нажмите /start"
        )
    
    elif choice == 4:
        # Изменение даты и времени
        await state.set_state(OrderStates.selecting_date)
        
        schedule = Config.get_pickup_schedule()
        
        text = "Выберите новую дату самовывоза:\n\n"
        buttons = []
        
        for date_str, times in schedule.items():
            start_hour = times["start"]
            end_hour = times["end"]
            text += f"{date_str} – с {start_hour}:00 до {end_hour}:00\n"
            buttons.append([InlineKeyboardButton(
                text=date_str,
                callback_data=f"date_{date_str}"
            )])
        
        text += "\nВыберите дату:"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await message.answer(text, reply_markup=keyboard)

