# vk-bot-mg

VK-бот для сбора заявок, задаёт пользователю ряд вопросов и сохраняет ответы в базу данных.

## Инструмент

- Python 3.12.0
- vk-api — работа с VK LongPoll
- SQLite — хранение заявок
- cryptography — шифрование персональных данных
- python-dotenv — конфигурация через `.env`

## Быстрый старт

### 1. Зависимости

Через **uv**:

```bash
uv sync
```

Или через **pip**:

```bash
pip install -r requirements.txt
```

### 2. Окружение

`.env` в корне проекта:

```env
VK_TOKEN=your_vk_token_here
SESSION_TIMEOUT=600       # таймаут сессии в секундах (по умолчанию 600)
DB_PATH=../quiz.db        # путь к файлу базы данных
KEY_PATH=../secret.key    # путь к файлу ключа шифрования
```

### 3. Запуск

```bash
python src/main.py
```

## Структура проекта

```
src/
  main.py        — точка входа
  config.py      — загрузка конфигурации из .env
  bot.py         — логика бота и шаги опроса
  database.py    — работа с SQLite
  encryption.py  — шифрование данных
  session.py     — управление сессиями пользователей
```
