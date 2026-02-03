"""
Утилиты для работы с датами
"""
from datetime import datetime, timedelta
from typing import Optional


def parse_date_string(date_str: str) -> Optional[datetime]:
    """
    Парсит строку даты в формате "15 марта" в datetime объект
    """
    # Русские названия месяцев
    months = {
        "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
        "мая": 5, "июня": 6, "июля": 7, "августа": 8,
        "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12
    }
    
    try:
        parts = date_str.split()
        if len(parts) != 2:
            return None
        
        day = int(parts[0])
        month_name = parts[1].lower()
        
        if month_name not in months:
            return None
        
        month = months[month_name]
        year = datetime.now().year
        
        # Если дата уже прошла в этом году, берем следующий год
        date_obj = datetime(year, month, day)
        if date_obj.date() < datetime.now().date():
            date_obj = datetime(year + 1, month, day)
        
        return date_obj
    except (ValueError, IndexError):
        return None


def get_date_from_string(date_str: str) -> Optional[datetime]:
    """Алиас для обратной совместимости"""
    return parse_date_string(date_str)





