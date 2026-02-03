import json
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
import aiofiles

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.orders_file = os.path.join(data_dir, "orders.json")
        self.order_counter_file = os.path.join(data_dir, "order_counter.json")
        self.users_file = os.path.join(data_dir, "users.json")
        self.stock_file = os.path.join(data_dir, "stock.json")
        os.makedirs(data_dir, exist_ok=True)
        self._init_files()
    
    def _init_files(self):
        """Инициализация файлов базы данных"""
        if not os.path.exists(self.orders_file):
            with open(self.orders_file, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
        
        if not os.path.exists(self.order_counter_file):
            with open(self.order_counter_file, "w", encoding="utf-8") as f:
                json.dump({"counter": 0}, f, ensure_ascii=False, indent=2)
        
        if not os.path.exists(self.users_file):
            with open(self.users_file, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
        
        if not os.path.exists(self.stock_file):
            # По умолчанию все товары доступны
            stock = {str(i): True for i in range(1, 7)}
            with open(self.stock_file, "w", encoding="utf-8") as f:
                json.dump(stock, f, ensure_ascii=False, indent=2)
    
    async def get_next_order_number(self) -> str:
        """Получить следующий номер заказа"""
        async with aiofiles.open(self.order_counter_file, "r", encoding="utf-8") as f:
            content = await f.read()
            data = json.loads(content)
            counter = data.get("counter", 0)
            counter += 1
            data["counter"] = counter
        
        async with aiofiles.open(self.order_counter_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))
        
        return f"{counter:03d}"
    
    async def save_order(self, order: Dict) -> str:
        """Сохранить заказ"""
        order_number = await self.get_next_order_number()
        order["order_number"] = order_number
        order["created_at"] = datetime.now().isoformat()
        order["status"] = "pending_payment"
        
        async with aiofiles.open(self.orders_file, "r", encoding="utf-8") as f:
            content = await f.read()
            orders = json.loads(content) if content else {}
        
        orders[order_number] = order
        
        async with aiofiles.open(self.orders_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(orders, ensure_ascii=False, indent=2))
        
        return order_number
    
    async def get_order(self, order_number: str) -> Optional[Dict]:
        """Получить заказ по номеру"""
        try:
            async with aiofiles.open(self.orders_file, "r", encoding="utf-8") as f:
                content = await f.read()
                if not content or not content.strip():
                    return None
                orders = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON в {self.orders_file}: {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при чтении {self.orders_file}: {e}", exc_info=True)
            return None
        
        return orders.get(order_number)
    
    async def update_order_status(self, order_number: str, status: str, **kwargs):
        """Обновить статус заказа"""
        try:
            async with aiofiles.open(self.orders_file, "r", encoding="utf-8") as f:
                content = await f.read()
                if not content or not content.strip():
                    orders = {}
                else:
                    orders = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON в {self.orders_file}: {e}")
            orders = {}
        except Exception as e:
            logger.error(f"Ошибка при чтении {self.orders_file}: {e}", exc_info=True)
            orders = {}
        
        if order_number in orders:
            orders[order_number]["status"] = status
            orders[order_number].update(kwargs)
            if "updated_at" not in orders[order_number]:
                orders[order_number]["updated_at"] = []
            orders[order_number]["updated_at"].append(datetime.now().isoformat())
        
        async with aiofiles.open(self.orders_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(orders, ensure_ascii=False, indent=2))
    
    async def get_user_orders(self, user_id: int) -> List[Dict]:
        """Получить все заказы пользователя"""
        try:
            async with aiofiles.open(self.orders_file, "r", encoding="utf-8") as f:
                content = await f.read()
                if not content or not content.strip():
                    return []
                orders = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON в {self.orders_file}: {e}")
            return []
        except Exception as e:
            logger.error(f"Ошибка при чтении {self.orders_file}: {e}", exc_info=True)
            return []
        
        return [order for order in orders.values() if order.get("user_id") == user_id]
    
    async def get_all_orders(self) -> Dict[str, Dict]:
        """Получить все заказы"""
        try:
            async with aiofiles.open(self.orders_file, "r", encoding="utf-8") as f:
                content = await f.read()
                if not content or not content.strip():
                    return {}
                return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON в {self.orders_file}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Ошибка при чтении {self.orders_file}: {e}", exc_info=True)
            return {}
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Получить данные пользователя"""
        try:
            async with aiofiles.open(self.users_file, "r", encoding="utf-8") as f:
                content = await f.read()
                if not content or not content.strip():
                    return None
                users = json.loads(content)
        except json.JSONDecodeError as e:
            # Файл поврежден - пытаемся восстановить
            logger.error(f"Ошибка парсинга JSON в {self.users_file}: {e}. Попытка восстановления...")
            try:
                # Пытаемся найти первый валидный JSON объект
                content = content.strip()
                # Ищем первую открывающую скобку
                start_idx = content.find('{')
                if start_idx != -1:
                    # Пытаемся найти соответствующую закрывающую скобку
                    brace_count = 0
                    end_idx = start_idx
                    for i in range(start_idx, len(content)):
                        if content[i] == '{':
                            brace_count += 1
                        elif content[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i + 1
                                break
                    
                    if brace_count == 0:
                        # Нашли валидный JSON объект
                        valid_content = content[start_idx:end_idx]
                        users = json.loads(valid_content)
                        # Сохраняем восстановленный файл
                        async with aiofiles.open(self.users_file, "w", encoding="utf-8") as f:
                            await f.write(json.dumps(users, ensure_ascii=False, indent=2))
                        logger.info(f"Файл {self.users_file} восстановлен")
                    else:
                        # Не удалось восстановить - создаем пустой файл
                        logger.warning(f"Не удалось восстановить {self.users_file}, создаем пустой файл")
                        users = {}
                        async with aiofiles.open(self.users_file, "w", encoding="utf-8") as f:
                            await f.write(json.dumps(users, ensure_ascii=False, indent=2))
                else:
                    # Нет валидного JSON - создаем пустой файл
                    users = {}
                    async with aiofiles.open(self.users_file, "w", encoding="utf-8") as f:
                        await f.write(json.dumps(users, ensure_ascii=False, indent=2))
            except Exception as restore_error:
                # Если восстановление не удалось - создаем пустой файл
                logger.error(f"Не удалось восстановить файл: {restore_error}", exc_info=True)
                users = {}
                async with aiofiles.open(self.users_file, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(users, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error(f"Неожиданная ошибка при чтении {self.users_file}: {e}", exc_info=True)
            return None
        
        user = users.get(str(user_id))
        if user:
            logger.debug(f"Найден пользователь {user_id}: consent_given={user.get('consent_given')}, phone={user.get('phone')}, first_name={user.get('first_name')}")
        else:
            logger.warning(f"Пользователь {user_id} не найден в базе. Доступные ключи: {list(users.keys())[:10]}")
        return user
    
    async def save_user(self, user_id: int, user_data: Dict):
        """Сохранить данные пользователя"""
        try:
            async with aiofiles.open(self.users_file, "r", encoding="utf-8") as f:
                content = await f.read()
                if not content or not content.strip():
                    users = {}
                else:
                    users = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON в {self.users_file} при сохранении: {e}. Создаем новый файл.")
            # Если файл поврежден, начинаем с пустого словаря
            users = {}
            # Пытаемся восстановить данные из поврежденного файла
            try:
                content = content.strip()
                start_idx = content.find('{')
                if start_idx != -1:
                    brace_count = 0
                    end_idx = start_idx
                    for i in range(start_idx, len(content)):
                        if content[i] == '{':
                            brace_count += 1
                        elif content[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i + 1
                                break
                    if brace_count == 0:
                        valid_content = content[start_idx:end_idx]
                        users = json.loads(valid_content)
            except Exception:
                pass  # Если не удалось восстановить, используем пустой словарь
        except Exception as e:
            logger.error(f"Ошибка при чтении {self.users_file}: {e}", exc_info=True)
            users = {}
        
        # Сохраняем существующие данные пользователя (например, consent_given, phone, first_name, last_name)
        existing_user = users.get(str(user_id), {})
        
        # Если у пользователя уже есть согласие, сохраняем его (не перезаписываем на False)
        if existing_user.get("consent_given") and "consent_given" not in user_data:
            user_data["consent_given"] = True
        
        # Сохраняем телефон, если он уже есть и не перезаписывается
        if existing_user.get("phone") and "phone" not in user_data:
            user_data["phone"] = existing_user.get("phone")
        
        # Сохраняем имя, если оно уже есть и не перезаписывается (и не пустое)
        if existing_user.get("first_name") and existing_user.get("first_name").strip() and "first_name" not in user_data:
            user_data["first_name"] = existing_user.get("first_name")
        
        if existing_user.get("last_name") and existing_user.get("last_name").strip() and "last_name" not in user_data:
            user_data["last_name"] = existing_user.get("last_name")
        
        users[str(user_id)] = {
            **existing_user,  # Сохраняем существующие данные
            **user_data,      # Обновляем новыми данными
            "updated_at": datetime.now().isoformat()
        }
        
        async with aiofiles.open(self.users_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(users, ensure_ascii=False, indent=2))
    
    async def update_user_consent(self, user_id: int, consented: bool = True):
        """Обновить согласие на обработку ПД"""
        user = await self.get_user(user_id)
        if user:
            user["consent_given"] = consented
            await self.save_user(user_id, user)
        else:
            await self.save_user(user_id, {"consent_given": consented})
    
    async def get_stock_status(self) -> Dict[str, bool]:
        """Получить статус остатков товаров"""
        try:
            async with aiofiles.open(self.stock_file, "r", encoding="utf-8") as f:
                content = await f.read()
                if not content or not content.strip():
                    # По умолчанию все товары доступны
                    return {str(i): True for i in range(1, 7)}
                return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON в {self.stock_file}: {e}")
            return {str(i): True for i in range(1, 7)}
        except Exception as e:
            logger.error(f"Ошибка при чтении {self.stock_file}: {e}", exc_info=True)
            return {str(i): True for i in range(1, 7)}
    
    async def is_variant_available(self, variant_num: int) -> bool:
        """Проверить, доступен ли вариант букета"""
        stock = await self.get_stock_status()
        return stock.get(str(variant_num), True)
    
    async def toggle_variant_stock(self, variant_num: int) -> bool:
        """Переключить доступность варианта букета"""
        try:
            async with aiofiles.open(self.stock_file, "r", encoding="utf-8") as f:
                content = await f.read()
                if not content or not content.strip():
                    stock = {str(i): True for i in range(1, 7)}
                else:
                    stock = json.loads(content)
            
            # Переключаем статус
            current_status = stock.get(str(variant_num), True)
            stock[str(variant_num)] = not current_status
            
            async with aiofiles.open(self.stock_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(stock, ensure_ascii=False, indent=2))
            
            logger.info(f"Вариант {variant_num} {'включен' if not current_status else 'выключен'}")
            return not current_status
        except Exception as e:
            logger.error(f"Ошибка при переключении остатков: {e}", exc_info=True)
            return False


