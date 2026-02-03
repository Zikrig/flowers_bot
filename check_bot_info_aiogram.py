"""
Альтернативный способ проверки информации о боте через aiogram
"""
import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден в переменных окружения!")
    print("Убедитесь, что файл .env существует и содержит BOT_TOKEN")
    exit(1)


async def get_bot_info():
    """Получить информацию о боте"""
    bot = Bot(token=BOT_TOKEN)
    
    try:
        bot_info = await bot.get_me()
        
        print("✅ Информация о боте:")
        print(f"   ID: {bot_info.id}")
        print(f"   Имя: {bot_info.first_name}")
        print(f"   Username: @{bot_info.username}" if bot_info.username else "   Username: не установлен")
        print(f"   Может присоединяться к группам: {bot_info.can_join_groups}")
        print(f"   Может читать сообщения: {bot_info.can_read_all_group_messages}")
        print(f"   Поддерживает inline-запросы: {bot_info.supports_inline_queries}")
        
        if bot_info.username:
            print(f"\n🔗 Ссылка на бота: https://t.me/{bot_info.username}")
        else:
            print("\n⚠️ Username не установлен. Установите его через @BotFather командой /setusername")
        
        await bot.session.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("   Проверьте правильность токена бота!")


if __name__ == "__main__":
    asyncio.run(get_bot_info())





