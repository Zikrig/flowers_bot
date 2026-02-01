import os
from dotenv import load_dotenv
from datetime import datetime
from typing import List

load_dotenv()


class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_IDS = [int(admin_id) for admin_id in os.getenv("ADMIN_IDS", "").split(",") if admin_id]
    
    # Google Sheets
    GOOGLE_SHEETS_CREDENTIALS_PATH = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", "credentials/service_account.json")
    GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
    GOOGLE_WORKSHEET_NAME = os.getenv("GOOGLE_WORKSHEET_NAME", "Заказы")
    
    
    # Payment
    PAYMENT_PHONE = os.getenv("PAYMENT_PHONE", "+79372431722")
    PAYMENT_RECEIVER = os.getenv("PAYMENT_RECEIVER", "Кузнецов А.А.")
    
    # Contacts
    ADMIN_CONTACTS = os.getenv("ADMIN_CONTACTS", "@fedorftp,@Dina_Kuznetsova75").split(",")
    PICKUP_ADDRESS = os.getenv("PICKUP_ADDRESS", "г. Вольск, ул. Клочкова, дом. 126")
    
    # Bouquet prices
    PRICE_15 = 1800
    PRICE_25 = 3000
    
    # Bouquet variants
    BOUQUET_VARIANTS = {
        1: {"name": "Микс", "photo": "data/photos/mix.jpg"},
        2: {"name": "Красный", "photo": "data/photos/red.jpg"},
        3: {"name": "Жёлтый", "photo": "data/photos/yellow.jpg"},
        4: {"name": "Белый", "photo": "data/photos/white.jpg"},
        5: {"name": "Жёлтый + фиолетовый", "photo": "data/photos/yellow_purple.jpg"},
        6: {"name": "Красный + жёлтый", "photo": "data/photos/red_yellow.jpg"},
    }
    
    # Pickup times (start and end hours)
    PICKUP_START_HOUR = 8
    PICKUP_END_HOUR = 19
    
    @staticmethod
    def get_pickup_schedule():
        """Генерирует расписание самовывоза на 7 дней вперед начиная с сегодня"""
        from datetime import datetime, timedelta
        import locale
        
        schedule = {}
        today = datetime.now().date()
        
        # Русские названия месяцев
        months = {
            1: "января", 2: "февраля", 3: "марта", 4: "апреля",
            5: "мая", 6: "июня", 7: "июля", 8: "августа",
            9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
        }
        
        for i in range(7):
            date = today + timedelta(days=i)
            day = date.day
            month = months[date.month]
            date_str = f"{day} {month}"
            
            # Определяем часы работы
            start_hour = Config.PICKUP_START_HOUR
            end_hour = Config.PICKUP_END_HOUR
            
            # В выходные можно изменить часы, если нужно
            # Например, в воскресенье (weekday() == 6) можно сделать другие часы
            if date.weekday() == 6:  # Воскресенье
                end_hour = 15  # До 15:00 в воскресенье
            
            schedule[date_str] = {"start": start_hour, "end": end_hour}
        
        return schedule


