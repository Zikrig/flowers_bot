"""
Скрипт для проверки информации о боте по токену
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден в переменных окружения!")
    print("Убедитесь, что файл .env существует и содержит BOT_TOKEN")
    exit(1)

# Получаем информацию о боте через Telegram Bot API
url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"

try:
    response = requests.get(url)
    data = response.json()
    
    if data.get("ok"):
        bot_info = data.get("result", {})
        print("✅ Информация о боте:")
        print(f"   ID: {bot_info.get('id')}")
        print(f"   Имя: {bot_info.get('first_name')}")
        print(f"   Username: @{bot_info.get('username', 'не установлен')}")
        print(f"   Может присоединяться к группам: {bot_info.get('can_join_groups', False)}")
        print(f"   Может читать сообщения: {bot_info.get('can_read_all_group_messages', False)}")
        print(f"   Поддерживает inline-запросы: {bot_info.get('supports_inline_queries', False)}")
        
        username = bot_info.get('username')
        if username:
            print(f"\n🔗 Ссылка на бота: https://t.me/{username}")
        else:
            print("\n⚠️ Username не установлен. Установите его через @BotFather командой /setusername")
    else:
        print(f"❌ Ошибка: {data.get('description', 'Неизвестная ошибка')}")
        if "Unauthorized" in str(data):
            print("   Проверьте правильность токена бота!")
            
except requests.exceptions.RequestException as e:
    print(f"❌ Ошибка при запросе к API: {e}")
except Exception as e:
    print(f"❌ Произошла ошибка: {e}")




