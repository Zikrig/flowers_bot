# Телеграм-бот для продажи тюльпанов

Бот на aiogram для продажи букетов тюльпанов с интеграцией Google Sheets и автоматической обработкой заказов.

## Возможности

- ✅ Выбор варианта букета (6 вариантов)
- ✅ Выбор количества тюльпанов (15 или 25 штук)
- ✅ Выбор даты и времени самовывоза
- ✅ Оформление заказа с подтверждением
- ✅ Ожидание оплаты с автоматической отменой через 24 часа
- ✅ Подтверждение оплаты администратором
- ✅ Интеграция с Google Sheets
- ✅ Создание бланков заказов
- ✅ Отмена заказов с возвратом средств
- ✅ Согласие на обработку персональных данных

## Требования

- Python 3.11+
- Docker и Docker Compose (опционально)
- Telegram Bot Token
- Google Service Account для работы с Google Sheets

## Установка

### 1. Клонирование репозитория

```bash
git clone <repository_url>
cd flowers_bot
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка переменных окружения

Скопируйте `env.example` в `.env` и заполните необходимые значения:

```bash
# Windows (PowerShell)
Copy-Item env.example .env

# Linux/Mac
cp env.example .env
```

**Подробная инструкция по настройке `.env` файла:** см. `ENV_SETUP.md`

Отредактируйте `.env`:

```env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789,987654321
GOOGLE_SHEETS_CREDENTIALS_PATH=credentials/service_account.json
GOOGLE_SHEET_ID=your_google_sheet_id_here
GOOGLE_WORKSHEET_NAME=Заказы
BOT_START_DATE=2026-02-15
BOT_END_DATE=2026-03-10
PAYMENT_PHONE=+79372431722
PAYMENT_RECEIVER=Кузнецов А.А.
ADMIN_CONTACTS=@fedorftp,@Dina_Kuznetsova75
PICKUP_ADDRESS=г. Вольск, ул. Клочкова, дом. 126
```

### 4. Настройка Google Sheets

1. Создайте проект в Google Cloud Console
2. Включите Google Sheets API и Google Drive API
3. Создайте Service Account и скачайте JSON ключ
4. Сохраните файл в `credentials/service_account.json`
5. Создайте Google таблицу и поделитесь ею с email из service account
6. Скопируйте ID таблицы из URL и вставьте в `GOOGLE_SHEET_ID`

### 5. Подготовка фотографий букетов

Поместите фотографии букетов в директорию `data/photos/` с именами:
- `mix.jpg` - Микс
- `red.jpg` - Красный
- `yellow.jpg` - Жёлтый
- `white.jpg` - Белый
- `yellow_purple.jpg` - Жёлтый + фиолетовый
- `red_yellow.jpg` - Красный + жёлтый

### 6. Запуск

#### Локальный запуск

```bash
python main.py
```

#### Запуск через Docker

```bash
docker-compose up -d
```

## Структура проекта

```
flowers_bot/
├── main.py                 # Точка входа
├── config.py               # Конфигурация
├── database.py             # Работа с локальной БД (JSON)
├── google_sheets.py        # Интеграция с Google Sheets
├── order_template.py       # Создание бланков заказов
├── handlers/               # Обработчики
│   ├── __init__.py
│   ├── common.py          # Общие команды
│   ├── order.py            # Оформление заказов
│   ├── payment.py          # Обработка оплаты
│   └── cancellation.py     # Отмена заказов
├── data/                   # Данные (создается автоматически)
│   ├── orders.json
│   └── order_counter.json
├── credentials/            # Учетные данные (не в git)
│   └── service_account.json
├── orders/                 # Бланки заказов (создается автоматически)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Использование

1. Пользователь запускает бота командой `/start`
2. Выбирает вариант букета (1-6)
3. Выбирает количество тюльпанов (15 или 25)
4. Может добавить еще букеты
5. Выбирает дату и время самовывоза
6. Вводит имя и фамилию
7. Подтверждает заказ
8. Отправляет квитанцию об оплате
9. Администратор подтверждает оплату
10. Заказ добавляется в Google Sheets и создается бланк

## Административные функции

Администраторы могут:
- Подтверждать или отклонять оплаты через кнопки
- Получать уведомления о новых заказах с квитанциями
- Видеть запросы на возврат средств
- Просматривать все заказы через команды
- Просматривать статистику и выручку
- Управлять заказами по статусам

### Команды администратора:
- `/admin_orders` — все заказы
- `/admin_orders_pending` — заказы, ожидающие оплаты
- `/admin_orders_paid` — оплаченные заказы
- `/admin_orders_today` — заказы на сегодня
- `/admin_order <номер>` — информация о заказе
- `/admin_stats` — статистика и выручка

**Подробная документация:** см. `ADMIN_GUIDE.md` и `ADMIN_QUICK_START.md`

## Автоматические функции

- Автоматическая отмена неоплаченных заказов через 24 часа
- Проверка сроков работы бота (15.02.2026 - 10.03.2026)
- Проверка возможности отмены заказа (более 48 часов до самовывоза)

## Лицензия

Проект создан для продажи тюльпанов от Кузнецовых.

