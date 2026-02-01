import json
import os
from typing import Dict, List, Optional
from datetime import datetime
import aiofiles


class Database:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.orders_file = os.path.join(data_dir, "orders.json")
        self.order_counter_file = os.path.join(data_dir, "order_counter.json")
        self.users_file = os.path.join(data_dir, "users.json")
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
        async with aiofiles.open(self.orders_file, "r", encoding="utf-8") as f:
            content = await f.read()
            orders = json.loads(content) if content else {}
        
        return orders.get(order_number)
    
    async def update_order_status(self, order_number: str, status: str, **kwargs):
        """Обновить статус заказа"""
        async with aiofiles.open(self.orders_file, "r", encoding="utf-8") as f:
            content = await f.read()
            orders = json.loads(content) if content else {}
        
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
        async with aiofiles.open(self.orders_file, "r", encoding="utf-8") as f:
            content = await f.read()
            orders = json.loads(content) if content else {}
        
        return [order for order in orders.values() if order.get("user_id") == user_id]
    
    async def get_all_orders(self) -> Dict[str, Dict]:
        """Получить все заказы"""
        async with aiofiles.open(self.orders_file, "r", encoding="utf-8") as f:
            content = await f.read()
            return json.loads(content) if content else {}
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Получить данные пользователя"""
        async with aiofiles.open(self.users_file, "r", encoding="utf-8") as f:
            content = await f.read()
            users = json.loads(content) if content else {}
        
        return users.get(str(user_id))
    
    async def save_user(self, user_id: int, user_data: Dict):
        """Сохранить данные пользователя"""
        async with aiofiles.open(self.users_file, "r", encoding="utf-8") as f:
            content = await f.read()
            users = json.loads(content) if content else {}
        
        # Сохраняем существующие данные пользователя (например, consent_given)
        existing_user = users.get(str(user_id), {})
        
        # Если у пользователя уже есть согласие, сохраняем его (не перезаписываем на False)
        if existing_user.get("consent_given") and "consent_given" not in user_data:
            user_data["consent_given"] = True
        
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


