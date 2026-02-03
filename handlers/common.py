from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from config import Config
from database import Database
import os

router = Router()
db = Database()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()
    
    # Сохраняем/обновляем данные пользователя из Telegram
    user = message.from_user
    
    # Получаем существующие данные пользователя (включая согласие, имя, телефон)
    existing_user = await db.get_user(user.id)
    
    # Сохраняем данные пользователя, но НЕ перезаписываем имя и телефон, если они уже есть
    user_data = {
        "username": user.username or "",
        "telegram_id": user.id
    }
    
    # Если у пользователя уже есть имя в базе (и оно не пустое), не перезаписываем его
    # Иначе используем имя из Telegram
    if existing_user and existing_user.get("first_name") and existing_user.get("first_name").strip():
        user_data["first_name"] = existing_user.get("first_name")
    else:
        user_data["first_name"] = user.first_name or ""
    
    if existing_user and existing_user.get("last_name") and existing_user.get("last_name").strip():
        user_data["last_name"] = existing_user.get("last_name")
    else:
        user_data["last_name"] = user.last_name or ""
    
    # Сохраняем телефон, если он есть в базе
    if existing_user and existing_user.get("phone"):
        user_data["phone"] = existing_user.get("phone")
    
    # Если у пользователя уже есть согласие, сохраняем его
    # Проверяем явно на True, чтобы не потерять согласие
    if existing_user and existing_user.get("consent_given") is True:
        user_data["consent_given"] = True
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Сохранение согласия для пользователя {user.id} при /start")
    
    await db.save_user(user.id, user_data)
    
    greeting = (
        "🌷 Привет! Это «Тюльпаны от Кузнецовых» — у нас все букеты по 15 и 25 тюльпанов, "
        "свежие, ровные и невероятно красивые!\n"
        "Нельзя изменить количество, но зато можно выбрать вариант букета\n\n"
        "💐 У нас 6 вариантов букетов — от нежного белого до яркого микса.\n"
        "🎁 Каждый букет упаковывается в пленку — у нас более 20 видов! "
        "Так что каждый букет выглядеть уникально.\n"
        "🎀 И, конечно, — лента в тон!\n\n"
        f"Цена букета 15 шт. — {Config.PRICE_15:,} ₽.\n"
        f"Цена букета 25 шт. — {Config.PRICE_25:,} ₽.\n\n"
        "Хотите выбрать свой идеальный букет к 8 Марта?\n\n"
        "👉 Нажмите «Выбрать букет»"
    )
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
    
    # Отправляем картинку с цветами, если она существует
    colors_photo_path = "data/colors.jpg"
    if os.path.exists(colors_photo_path):
        await message.answer_photo(photo=FSInputFile(colors_photo_path))
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Выбрать букет", callback_data="start_order")],
        [InlineKeyboardButton(text="Мои заказы", callback_data="my_orders")]
    ])
    
    await message.answer(greeting, reply_markup=keyboard)


@router.callback_query(F.data == "start_order")
async def start_order(callback: CallbackQuery, state: FSMContext):
    """Начало оформления заказа"""
    from handlers.order import show_bouquet_selection
    await show_bouquet_selection(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "my_orders")
async def show_my_orders(callback: CallbackQuery):
    """Показать заказы пользователя"""
    user_id = callback.from_user.id
    orders = await db.get_user_orders(user_id)
    
    if not orders:
        await callback.message.answer("У вас пока нет заказов.")
        await callback.answer()
        return
    
    text = "📋 Ваши заказы:\n\n"
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    
    for order in orders:
        status_emoji = {
            "pending_payment": "⏳",
            "paid": "✅",
            "cancelled": "❌",
            "completed": "🎉"
        }.get(order.get("status", ""), "❓")
        
        order_number = order.get('order_number', 'N/A')
        status_text = {
            "pending_payment": "Ожидает оплаты",
            "paid": "Оплачен",
            "cancelled": "Отменен",
            "completed": "Выполнен"
        }.get(order.get("status", ""), "Неизвестно")
        
        text += (
            f"{status_emoji} Заказ №{order_number}\n"
            f"Статус: {status_text}\n"
            f"Сумма: {order.get('total_price', 0):,} ₽\n"
            f"Самовывоз: {order.get('pickup_date', 'N/A')} в {order.get('pickup_time', 'N/A')}\n\n"
        )
        
        # Добавляем кнопку отмены только для оплаченных заказов
        if order.get("status") == "paid":
            buttons.append([
                InlineKeyboardButton(
                    text=f"❌ Отменить заказ №{order_number}",
                    callback_data=f"cancel_order_{order_number}"
                )
            ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
    
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = (
        "🌷 Бот для заказа букетов тюльпанов\n\n"
        "Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n\n"
        "Для заказа букета нажмите кнопку «Выбрать букет»"
    )
    await message.answer(help_text)


@router.message(F.text.in_(["Хочу букет", "хочу букет", "ХОЧУ БУКЕТ"]))
async def want_bouquet(message: Message, state: FSMContext):
    """Обработчик текста 'Хочу букет'"""
    from handlers.order import show_bouquet_selection
    await show_bouquet_selection(message, state)

