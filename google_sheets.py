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
            "статус",
            "№ заказа",
            "Дата и время",
            "Фамилия, Имя",
            "@ телеграм",
            "№ варианта",
            "кол-во букетов",
            "кол-во тюльпанов",
            "итого тюльпанов",
            "сумма",
            "оплата",
            "возврат"
        ]
        
        self.worksheet.append_row(headers)
    
    def add_order(self, order: Dict):
        """Добавить заказ в таблицу (создает несколько строк - по одной на каждый вариант букета)"""
        if not self.worksheet:
            print("Warning: Google Sheets not connected")
            return
        
        order_number = order.get("order_number", "")
        
        # Проверяем, не существует ли уже заказ в таблице
        try:
            existing_cells = self.worksheet.findall(order_number)
            if existing_cells:
                print(f"Order {order_number} already exists in sheet, skipping add")
                return
        except:
            pass  # Если не найдено, продолжаем
        
        # Общие данные заказа
        status = order.get("status", "pending_payment")
        pickup_date = order.get("pickup_date", "")
        pickup_time = order.get("pickup_time", "")
        # Объединяем дату и время: "7 марта, 10:00"
        date_time = f"{pickup_date}, {pickup_time}" if pickup_date and pickup_time else ""
        
        # Объединяем фамилию и имя: "Иванов Иван"
        full_name = f"{order.get('last_name', '')} {order.get('first_name', '')}".strip()
        
        # Форматируем username: добавляем "@" если его нет
        username = order.get("username", "")
        if username and not username.startswith("@"):
            username = f"@{username}"
        
        total_price = order.get("total_price", 0)
        
        # Определяем статус для отображения
        status_display = "оплачен" if status == "paid" else "отменен" if status == "cancelled" else "ожидает оплаты"
        
        # Сумма оплаты (равна сумме заказа, если оплачен)
        payment_amount = total_price if status == "paid" else 0
        
        # Создаем строку для каждого варианта букета
        rows_to_add = []
        bouquets = order.get("bouquets", [])
        
        for bouquet in bouquets:
            variant_num = bouquet.get("variant", "")
            count = bouquet.get("count", 0)  # количество букетов этого варианта
            quantity = bouquet.get("quantity", 0)  # количество тюльпанов в букете
            total_tulips = count * quantity  # итого тюльпанов для этого варианта
            
            row = [
                status_display,
                order_number,
                date_time,
                full_name,
                username,
                variant_num,
                count,
                quantity,
                total_tulips,
                total_price,  # общая сумма заказа (повторяется для всех строк)
                payment_amount,  # сумма оплаты (повторяется для всех строк)
                ""  # возврат (пусто по умолчанию)
            ]
            rows_to_add.append(row)
        
        # Добавляем все строки заказа
        if rows_to_add:
            self.worksheet.append_rows(rows_to_add)
    
    def update_order_status(self, order_number: str, status: str, **kwargs):
        """Обновить статус заказа в таблице (обновляет все строки заказа)"""
        if not self.worksheet:
            return
        
        try:
            # Найти все строки с номером заказа (заказ может занимать несколько строк)
            cells = self.worksheet.findall(order_number)
            if not cells:
                print(f"Order {order_number} not found in sheet")
                return
            
            # Определяем статус для отображения
            status_display = "оплачен" if status == "paid" else "отменен" if status == "cancelled" else "ожидает оплаты"
            
            # Получаем данные заказа для обновления суммы оплаты
            order = kwargs.get("order")
            if order:
                total_price = order.get("total_price", 0)
                payment_amount = total_price if status == "paid" else 0
            else:
                # Если заказ не передан, пытаемся получить сумму из существующих строк
                first_row = cells[0].row
                try:
                    total_price = self.worksheet.cell(first_row, 10).value  # колонка "сумма"
                    payment_amount = total_price if status == "paid" else 0
                except:
                    payment_amount = 0
            
            refund_amount = kwargs.get("refund_amount", "")
            
            # Обновляем все строки заказа
            for cell in cells:
                row = cell.row
                # Обновить статус (колонка 1)
                self.worksheet.update_cell(row, 1, status_display)
                
                # Обновить сумму оплаты (колонка 11)
                self.worksheet.update_cell(row, 11, payment_amount)
                
                # Обновить возврат (колонка 12) если есть
                if refund_amount:
                    self.worksheet.update_cell(row, 12, refund_amount)
                    
        except Exception as e:
            print(f"Error updating order {order_number} in sheet: {e}")


