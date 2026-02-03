import gspread
from google.oauth2.service_account import Credentials
from typing import Dict, List
import os
from config import Config
import json
import time
import traceback


# region agent log
_DEBUG_LOG_PATHS = [
    r"c:\Users\Ф\Desktop\freelance\flowers_bot\.cursor\debug.log",  # host path (Cursor workspace)
    r"/app/.cursor/debug.log",  # docker path (mounted from ./.cursor)
    os.path.join(".cursor", "debug.log"),  # relative fallback
]


def _dbg_log(hypothesisId: str, location: str, message: str, data: Dict):
    """Write one NDJSON line for debug-mode. Avoid secrets/PII."""
    payload = {
        "sessionId": "debug-session",
        "runId": os.getenv("DEBUG_RUN_ID", "pre-fix"),
        "hypothesisId": hypothesisId,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    line = json.dumps(payload, ensure_ascii=False)
    for p in _DEBUG_LOG_PATHS:
        try:
            os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(line + "\n")
            return
        except Exception:
            continue
# endregion


class GoogleSheets:
    def __init__(self):
        self.credentials_path = Config.GOOGLE_SHEETS_CREDENTIALS_PATH
        self.sheet_id = Config.GOOGLE_SHEET_ID
        self.worksheet_name = Config.GOOGLE_WORKSHEET_NAME
        self.client = None
        self.sheet = None
        self.worksheet = None
        # region agent log
        _dbg_log(
            "A",
            "google_sheets.py:GoogleSheets.__init__",
            "init",
            {
                "has_sheet_id": bool(self.sheet_id),
                "worksheet_name": self.worksheet_name,
                "credentials_path": self.credentials_path,
                "credentials_exists": bool(self.credentials_path and os.path.exists(self.credentials_path)),
            },
        )
        # endregion
        self._connect()
    
    def ensure_connected(self):
        """Убедиться, что подключение установлено"""
        if not self.worksheet and self.sheet_id:
            self._connect()
    
    def _connect(self):
        """Подключение к Google Sheets"""
        # region agent log
        _dbg_log(
            "A",
            "google_sheets.py:GoogleSheets._connect",
            "connect_start",
            {
                "has_sheet_id": bool(self.sheet_id),
                "worksheet_name": self.worksheet_name,
                "credentials_path": self.credentials_path,
                "credentials_exists": bool(self.credentials_path and os.path.exists(self.credentials_path)),
            },
        )
        # endregion
        if not os.path.exists(self.credentials_path):
            print(f"Warning: Credentials file not found at {self.credentials_path}")
            # region agent log
            _dbg_log(
                "B",
                "google_sheets.py:GoogleSheets._connect",
                "credentials_missing",
                {"credentials_path": self.credentials_path},
            )
            # endregion
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
        # region agent log
        _dbg_log(
            "A",
            "google_sheets.py:GoogleSheets._connect",
            "connect_end",
            {
                "connected": bool(self.worksheet),
                "sheet_opened": bool(self.sheet),
            },
        )
        # endregion
    
    def _init_headers(self):
        """Инициализация заголовков таблицы (при создании нового листа)"""
        if not self.worksheet:
            return
        
        # Первая строка заголовков
        header_row1 = [
            "статус",
            "№ заказа",
            "дата и время готовности",
            "Фамилия, Имя",
            "@ телеграм",
            "№ варианта",  # Будет объединено с 6 колонками для вариантов
            "", "", "", "", "",  # Место для вариантов 1-6
            "итого букетов",
            "итого тюльпанов",
            "сумма",
            "оплата",
            "возврат"
        ]
        
        # Вторая строка заголовков (подзаголовки для вариантов)
        header_row2 = [
            "",  # статус
            "",  # № заказа
            "",  # дата и время готовности
            "",  # Фамилия, Имя
            "",  # @ телеграм
            "1 (микс)",
            "2 (красный)",
            "3 (желтый)",
            "4 (белый)",
            "5 (фиол+желт)",
            "6 (красн+желт)",
            "",  # итого букетов
            "",  # итого тюльпанов
            "",  # сумма
            "",  # оплата
            ""   # возврат
        ]
        
        self.worksheet.append_row(header_row1)
        self.worksheet.append_row(header_row2)
    
    def init_headers(self):
        """Инициализация заголовков таблицы при каждом запуске (перезаписывает первые две строки)"""
        # Убеждаемся, что подключение установлено
        self.ensure_connected()
        
        if not self.worksheet:
            print("Warning: Google Sheets not connected")
            # region agent log
            _dbg_log(
                "A",
                "google_sheets.py:GoogleSheets.init_headers",
                "no_worksheet",
                {"has_sheet_id": bool(self.sheet_id)},
            )
            # endregion
            return False
        
        # Первая строка заголовков
        header_row1 = [
            "статус",
            "№ заказа",
            "дата и время готовности",
            "Фамилия, Имя",
            "@ телеграм",
            "№ варианта",
            "", "", "", "", "",  # Место для вариантов 1-6
            "итого букетов",
            "итого тюльпанов",
            "сумма",
            "оплата",
            "возврат"
        ]
        
        # Вторая строка заголовков (подзаголовки для вариантов)
        header_row2 = [
            "",  # статус
            "",  # № заказа
            "",  # дата и время готовности
            "",  # Фамилия, Имя
            "",  # @ телеграм
            "1 (микс)",
            "2 (красный)",
            "3 (желтый)",
            "4 (белый)",
            "5 (фиол+желт)",
            "6 (красн+желт)",
            "",  # итого букетов
            "",  # итого тюльпанов
            "",  # сумма
            "",  # оплата
            ""   # возврат
        ]
        
        try:
            # Получаем все данные из таблицы
            all_values = self.worksheet.get_all_values()
            
            print(f"Initializing headers. Current rows in sheet: {len(all_values)}")
            # region agent log
            _dbg_log(
                "A",
                "google_sheets.py:GoogleSheets.init_headers",
                "before_replace",
                {"rows": len(all_values)},
            )
            # endregion
            
            # Всегда обновляем первые две строки через update
            # Если строк меньше двух, добавляем недостающие
            if len(all_values) >= 2:
                # Обновляем существующие первые две строки (без сдвига данных)
                r1 = self.worksheet.update("A1:P1", [header_row1])
                r2 = self.worksheet.update("A2:P2", [header_row2])
                # region agent log
                _dbg_log(
                    "A",
                    "google_sheets.py:GoogleSheets.init_headers",
                    "updated_header_rows",
                    {
                        "update1": r1,
                        "update2": r2,
                    },
                )
                # endregion
                return True
            elif len(all_values) == 1:
                # Обновляем первую строку и добавляем вторую
                r1 = self.worksheet.update("A1:P1", [header_row1])
                self.worksheet.insert_row(header_row2, 2)
                # region agent log
                _dbg_log(
                    "A",
                    "google_sheets.py:GoogleSheets.init_headers",
                    "updated_row1_inserted_row2",
                    {"update1": r1},
                )
                # endregion
                return True
            else:
                # Если таблица пустая, вставляем заголовки
                self.worksheet.insert_row(header_row2, 1)  # Сначала вторую строку
                self.worksheet.insert_row(header_row1, 1)  # Потом первую строку (она будет выше)
                print("Inserted header rows into empty sheet")
                # region agent log
                _dbg_log(
                    "A",
                    "google_sheets.py:GoogleSheets.init_headers",
                    "inserted_into_empty",
                    {},
                )
                # endregion
                return True
            
        except Exception as e:
            print(f"Error initializing headers: {e}")
            traceback.print_exc()
            # region agent log
            _dbg_log(
                "E",
                "google_sheets.py:GoogleSheets.init_headers",
                "exception",
                {"error": str(e), "trace": traceback.format_exc()[:1000]},
            )
            # endregion
            # Если произошла ошибка, пробуем другой способ
            try:
                # Пробуем удалить первые две строки и вставить новые
                all_values = self.worksheet.get_all_values()
                if len(all_values) >= 2:
                    self.worksheet.delete_rows(1, 2)
                elif len(all_values) == 1:
                    self.worksheet.delete_rows(1, 1)
                # Вставляем новые заголовки
                self.worksheet.insert_row(header_row2, 1)
                self.worksheet.insert_row(header_row1, 1)
                print("Used fallback method to insert headers")
                # region agent log
                _dbg_log(
                    "E",
                    "google_sheets.py:GoogleSheets.init_headers",
                    "fallback_insert_ok",
                    {},
                )
                # endregion
                return True
            except Exception as e2:
                print(f"Error adding headers as fallback: {e2}")
                traceback.print_exc()
                # region agent log
                _dbg_log(
                    "E",
                    "google_sheets.py:GoogleSheets.init_headers",
                    "fallback_insert_failed",
                    {"error": str(e2), "trace": traceback.format_exc()[:1000]},
                )
                # endregion
                return False
    
    def add_order(self, order: Dict):
        """Добавить заказ в таблицу (создает две строки: количество букетов и количество тюльпанов по вариантам)"""
        # region agent log
        _dbg_log(
            "C",
            "google_sheets.py:GoogleSheets.add_order",
            "enter",
            {
                "has_worksheet": bool(self.worksheet),
                "order_number_present": bool(order.get("order_number")),
                "status": order.get("status"),
                "bouquets_len": len(order.get("bouquets", []) or []),
            },
        )
        # endregion
        if not self.worksheet:
            print("Warning: Google Sheets not connected")
            # region agent log
            _dbg_log(
                "D",
                "google_sheets.py:GoogleSheets.add_order",
                "no_worksheet",
                {},
            )
            # endregion
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
        
        # Группируем букеты по варианту
        # Словарь: {variant_num: {"bouquet_count": сумма букетов, "tulip_count": сумма тюльпанов}}
        variants_data = {}
        bouquets = order.get("bouquets", [])
        
        total_bouquets = 0
        total_tulips = 0
        
        for bouquet in bouquets:
            variant_num = bouquet.get("variant", "")
            count = bouquet.get("count", 0)  # количество букетов этого варианта
            quantity = bouquet.get("quantity", 0)  # количество тюльпанов в букете
            tulips_for_variant = count * quantity  # итого тюльпанов для этого варианта
            
            if variant_num not in variants_data:
                variants_data[variant_num] = {"bouquet_count": 0, "tulip_count": 0}
            
            variants_data[variant_num]["bouquet_count"] += count
            variants_data[variant_num]["tulip_count"] += tulips_for_variant
            
            total_bouquets += count
            total_tulips += tulips_for_variant
        
        # Создаем первую строку: количество букетов по вариантам
        row1 = [
            status_display,
            order_number,
            date_time,
            full_name,
            username,
            # "",  # № варианта (заголовок)
            variants_data.get(1, {}).get("bouquet_count", ""),  # вариант 1
            variants_data.get(2, {}).get("bouquet_count", ""),  # вариант 2
            variants_data.get(3, {}).get("bouquet_count", ""),  # вариант 3
            variants_data.get(4, {}).get("bouquet_count", ""),  # вариант 4
            variants_data.get(5, {}).get("bouquet_count", ""),  # вариант 5
            variants_data.get(6, {}).get("bouquet_count", ""),  # вариант 6
            total_bouquets,  # итого букетов
            total_tulips,  # итого тюльпанов
            total_price,  # сумма
            payment_amount,  # оплата
            ""  # возврат
        ]
        
        # Создаем вторую строку: количество тюльпанов по вариантам
        row2 = [
            "",  # статус
            "",  # № заказа
            "",  # дата и время готовности
            "",  # Фамилия, Имя
            "",  # @ телеграм
            "",  # № варианта
            variants_data.get(1, {}).get("tulip_count", ""),  # вариант 1
            variants_data.get(2, {}).get("tulip_count", ""),  # вариант 2
            variants_data.get(3, {}).get("tulip_count", ""),  # вариант 3
            variants_data.get(4, {}).get("tulip_count", ""),  # вариант 4
            variants_data.get(5, {}).get("tulip_count", ""),  # вариант 5
            variants_data.get(6, {}).get("tulip_count", ""),  # вариант 6
            "",  # итого букетов
            "",  # итого тюльпанов
            "",  # сумма
            "",  # оплата
            ""   # возврат
        ]
        
        # Добавляем обе строки заказа
        try:
            self.worksheet.append_rows([row1, row2])
            # region agent log
            _dbg_log(
                "E",
                "google_sheets.py:GoogleSheets.add_order",
                "append_rows_ok",
                {"order_number": order_number},
            )
            # endregion
        except Exception as e:
            # region agent log
            _dbg_log(
                "E",
                "google_sheets.py:GoogleSheets.add_order",
                "append_rows_failed",
                {"order_number": order_number, "error": str(e), "trace": traceback.format_exc()[:1000]},
            )
            # endregion
            raise
    
    def update_order_status(self, order_number: str, status: str, **kwargs):
        """Обновить статус заказа в таблице (обновляет первую строку заказа, где находятся статус, сумма, оплата, возврат)"""
        if not self.worksheet:
            return
        
        try:
            # Найти первую строку с номером заказа (заказ занимает две строки: первая - количество букетов, вторая - количество тюльпанов)
            cells = self.worksheet.findall(order_number)
            if not cells:
                print(f"Order {order_number} not found in sheet")
                return
            
            # Берем первую найденную строку (это строка с количеством букетов, где находятся статус, сумма, оплата, возврат)
            first_row = cells[0].row
            
            # Определяем статус для отображения
            status_display = "оплачен" if status == "paid" else "отменен" if status == "cancelled" else "ожидает оплаты"
            
            # Получаем данные заказа для обновления суммы оплаты
            order = kwargs.get("order")
            if order:
                total_price = order.get("total_price", 0)
                payment_amount = total_price if status == "paid" else 0
            else:
                # Если заказ не передан, пытаемся получить сумму из существующей строки
                try:
                    # Колонка "сумма" = 15 (после: статус, № заказа, дата, имя, телеграм, № варианта, 6 вариантов, итого букетов, итого тюльпанов)
                    total_price = self.worksheet.cell(first_row, 15).value
                    payment_amount = total_price if status == "paid" else 0
                except:
                    payment_amount = 0
            
            refund_amount = kwargs.get("refund_amount", "")
            
            # Обновляем первую строку заказа
            # Статус (колонка 1)
            self.worksheet.update_cell(first_row, 1, status_display)
            
            # Сумма оплаты (колонка 16 - "оплата")
            self.worksheet.update_cell(first_row, 16, payment_amount)
                
            # Возврат (колонка 17 - "возврат") если есть
            if refund_amount:
                self.worksheet.update_cell(first_row, 17, refund_amount)
                    
        except Exception as e:
            print(f"Error updating order {order_number} in sheet: {e}")


