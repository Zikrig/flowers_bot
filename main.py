import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import Config
from handlers import common, order, payment, cancellation, admin

# Настройка логирования
# import os
# from logging.handlers import RotatingFileHandler

# log_dir = "logs"
# os.makedirs(log_dir, exist_ok=True)

# Настройка логирования в файл и консоль
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # RotatingFileHandler(
        #     os.path.join(log_dir, "bot.log"),
        #     maxBytes=10*1024*1024,  # 10 MB
        #     backupCount=3,
        #     encoding='utf-8'
        # ),
        logging.StreamHandler()  # Также выводим в консоль
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """Основная функция запуска бота"""
    if not Config.BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен в переменных окружения!")
        return
    
    # Инициализация бота и диспетчера
    bot = Bot(token=Config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация роутеров
    dp.include_router(common.router)
    dp.include_router(order.router)
    dp.include_router(payment.router)
    dp.include_router(cancellation.router)
    dp.include_router(admin.router)
    
    # Запуск фоновой задачи для проверки неоплаченных заказов
    asyncio.create_task(check_unpaid_orders_background(bot))
    
    logger.info("Бот запущен и готов к работе!")
    
    # Запуск polling
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


async def check_unpaid_orders_background(bot: Bot):
    """Фоновая задача для проверки неоплаченных заказов"""
    from database import Database
    from datetime import datetime, timedelta
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    db = Database()
    
    while True:
        try:
            orders = await db.get_all_orders()
            now = datetime.now()
            
            for order_number, order in orders.items():
                if order.get("status") != "pending_payment":
                    continue
                
                created_at_str = order.get("created_at")
                if not created_at_str:
                    continue
                
                created_at = datetime.fromisoformat(created_at_str)
                time_diff = now - created_at
                
                # Если прошло более 24 часов
                if time_diff > timedelta(hours=24):
                    await db.update_order_status(order_number, "cancelled", reason="timeout")
                    
                    user_id = order.get("user_id")
                    cancellation_text = (
                        "К сожалению, оплата по заказу не поступила в течение 24 часов.\n"
                        f"Ваш заказ №{order_number} автоматически отменён.\n\n"
                        "Хотите оформить новый? Просто напишите «Хочу букет»! 🌷"
                    )
                    
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Хочу букет", callback_data="start_order")]
                    ])
                    
                    try:
                        await bot.send_message(user_id, cancellation_text, reply_markup=keyboard)
                    except Exception as e:
                        logger.error(f"Error sending cancellation to user {user_id}: {e}")
        
        except Exception as e:
            logger.error(f"Error checking unpaid orders: {e}")
        
        # Проверяем каждые 30 минут
        await asyncio.sleep(1800)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")

