"""
Скрипт для создания необходимых директорий проекта
"""
import os

directories = [
    "data",
    "data/photos",
    "credentials",
    "orders"
]

for directory in directories:
    os.makedirs(directory, exist_ok=True)
    print(f"✓ Создана директория: {directory}")

print("\nВсе директории созданы!")
print("\nНе забудьте:")
print("1. Добавить фотографии букетов в data/photos/")
print("2. Добавить service_account.json в credentials/")
print("3. Создать файл .env с настройками")


