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
    PAYMENT_PHONE = os.getenv("PAYMENT_PHONE", "89881664153")
    PAYMENT_RECEIVER = os.getenv("PAYMENT_RECEIVER", "Дина К.")
    
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
        """Возвращает фиксированное расписание самовывоза"""
        schedule = {
            "3 февраля": {"start": 8, "end": 15},
            "5 марта": {"start": 8, "end": 19},
            "6 марта": {"start": 7, "end": 19},
            "7 марта": {"start": 8, "end": 19},
            "8 марта": {"start": 8, "end": 15}
        }
        return schedule


