import gspread
from google.oauth2.service_account import Credentials
from typing import Dict, List
import os
from config import Config


class GoogleSheets:
    def __init__(self):
        self.credentials_path = Config.GOOGLE_SHEETS_CREDENTIALS_PATH
        self.sheet_id = Config.GOOGLE_SHEET_ID
        self.worksheet_name = Config.GOOGLE_WORKSHEET_NAME
        self.client = None
        self.sheet = None
        self.worksheet = None
        self._connect()
    
    def _connect(self):
        """Подключение к Google Sheets"""
        if not os.path.exists(self.credentials_path):
            print(f"Warning: Credentials file not found at {self.credentials_path}")
            return
        
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds = Credentials.from_service_account_file(
            self.credentials_path,
            scopes=scope
        )
        
        self.client = gspread.authorize(creds)
        
        if self.sheet_id:
            self.sheet = self.client.open_by_key(self.sheet_id)
            try:
                self.worksheet = self.sheet.worksheet(self.worksheet_name)
            except gspread.exceptions.WorksheetNotFound:
                self.worksheet = self.sheet.add_worksheet(
                    title=self.worksheet_name,
                    rows=1000,
                    cols=20
                )
                self._init_headers()
    
    def _init_headers(self):
        """Инициализация заголовков таблицы"""
        if not self.worksheet:
            return
        
        headers = [
            "Статус",
            "Номер заказа",
            "Дата самовывоза",
            "Время самовывоза",
            "Фамилия",
            "Имя",
            "Ник в Telegram",
            "Варианты букетов",
            "Количество тюльпанов",
            "Количество букетов",
            "Сумма заказа",
            "Оплата",
            "Дата создания",
            "Номер карты для возврата"
        ]
        
        self.worksheet.append_row(headers)
    
    def add_order(self, order: Dict):
        """Добавить заказ в таблицу"""
        if not self.worksheet:
            print("Warning: Google Sheets not connected")
            return
        
        # Форматирование вариантов букетов
        bouquets_info = []
        for bouquet in order.get("bouquets", []):
            variant_name = bouquet.get("variant_name", "")
            quantity = bouquet.get("quantity", 0)
            count = bouquet.get("count", 0)
            bouquets_info.append(f"{variant_name} - {quantity} шт. - {count} букет")
        
        bouquets_str = "; ".join(bouquets_info)
        
        # Подсчет общего количества букетов
        total_bouquets = sum(b.get("count", 0) for b in order.get("bouquets", []))
        
        row = [
            order.get("status", "pending_payment"),
            order.get("order_number", ""),
            order.get("pickup_date", ""),
            order.get("pickup_time", ""),
            order.get("last_name", ""),
            order.get("first_name", ""),
            order.get("username", ""),
            bouquets_str,
            f"{order.get('bouquets', [{}])[0].get('quantity', '')} шт." if order.get("bouquets") else "",
            total_bouquets,
            order.get("total_price", 0),
            "Да" if order.get("status") == "paid" else "Нет",
            order.get("created_at", ""),
            order.get("refund_card", "")
        ]
        
        self.worksheet.append_row(row)
    
    def update_order_status(self, order_number: str, status: str, **kwargs):
        """Обновить статус заказа в таблице"""
        if not self.worksheet:
            return
        
        try:
            # Найти строку с номером заказа
            cell = self.worksheet.find(order_number)
            if cell:
                row = cell.row
                # Обновить статус (колонка A)
                self.worksheet.update_cell(row, 1, status)
                
                # Обновить оплату (колонка L)
                if status == "paid":
                    self.worksheet.update_cell(row, 12, "Да")
                elif status == "cancelled":
                    self.worksheet.update_cell(row, 12, "Отменено")
                
                # Обновить номер карты для возврата если есть
                if kwargs.get("refund_card"):
                    self.worksheet.update_cell(row, 14, kwargs["refund_card"])
        except gspread.exceptions.CellNotFound:
            print(f"Order {order_number} not found in sheet")


