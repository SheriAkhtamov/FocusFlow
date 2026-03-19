# FocusFlow

**FocusFlow** — это умный менеджер задач с AI-напоминаниями, веб-интерфейсом и Telegram-ботом.  
Проект позволяет создавать задачи вручную, текстом через AI или голосом, отслеживать дедлайны в календаре и получать уведомления по мере приближения срока.

---

## Возможности

- Веб-приложение на **FastAPI**
- Авторизация пользователей через **JWT в cookie**
- Хранение данных в **PostgreSQL**
- Управление задачами:
  - создание
  - удаление
  - отметка о выполнении
  - просмотр по дням
  - календарный режим
- AI-парсинг задач из текста
- Распознавание голосовых сообщений и автоматическое создание задач
- Telegram-бот для:
  - привязки аккаунта
  - просмотра сегодняшних задач
  - добавления новых задач голосом
- Напоминания о дедлайнах:
  - в браузере через **SSE**
  - в Telegram
- Админ-панель для управления пользователями
- Docker-окружение для быстрого запуска

---

## Стек технологий

- **Python 3.12**
- **FastAPI**
- **Uvicorn**
- **Jinja2**
- **SQLAlchemy Async**
- **PostgreSQL**
- **APScheduler**
- **Aiogram 3**
- **Google Gemini API**
- **Docker / Docker Compose**
- **TailwindCSS** (через CDN в шаблонах)

---

## Архитектура проекта

```text
.
├── bot.py
├── config.py
├── docker-compose.yml
├── Dockerfile
├── main.py
├── requirements.txt
├── models/
│   ├── database.py
│   └── __init__.py
├── routers/
│   ├── admin.py
│   ├── api.py
│   ├── auth.py
│   ├── notifications.py
│   ├── tasks.py
│   └── __init__.py
├── services/
│   ├── ai_service.py
│   ├── scheduler.py
│   └── __init__.py
└── templates/
    ├── admin_create_user.html
    ├── admin_users.html
    ├── base.html
    ├── calendar.html
    ├── day_tasks.html
    ├── index.html
    ├── login.html
    └── settings.html



---

## Как это работает

### Веб-интерфейс

Пользователь входит в систему, создаёт задачи и видит их:

* на главной странице
* по срочности
* в календаре
* по конкретному дню

### AI-функции

Можно:

* ввести задачу обычным текстом
* продиктовать задачу голосом

AI извлекает:

* название задачи
* дедлайн
* тип задачи

### Telegram-бот

Бот позволяет:

* привязать аккаунт через deep link
* открыть меню
* посмотреть активные задачи
* отправить голосовое сообщение для создания новой задачи

### Уведомления

Когда дедлайн приближается, приложение отправляет напоминания:

* в браузер через Server-Sent Events
* в Telegram, если аккаунт привязан

---

## Основные роуты

### Web

* `/` — список задач
* `/login` — вход
* `/logout` — выход
* `/calendar` — календарь
* `/calendar/{YYYY-MM-DD}` — задачи за конкретный день
* `/settings` — настройки и привязка Telegram
* `/admin/users` — админ-панель пользователей

### API

* `POST /api/parse_task` — парсинг задачи из текста
* `POST /api/voice_task` — распознавание голосового сообщения и парсинг задачи
* `GET /api/notifications/stream` — поток уведомлений через SSE

---

## Быстрый запуск через Docker

### 1. Клонировать репозиторий

```bash
git clone https://github.com/your-username/focusflow.git
cd focusflow
```

### 2. Создать `config.py`

Создай файл `config.py` в корне проекта:

```python
# Telegram
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

# Google Gemini
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"

# FastAPI / Auth
SECRET_KEY = "your-long-random-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

# Database
DATABASE_URL = "postgresql+asyncpg://brainfucker:brainfucker@db:5432/brainfucker"

# Superadmin
SUPERADMIN_USERNAME = "admin"
SUPERADMIN_PASSWORD = "admin123"
```

### 3. Запустить контейнеры

```bash
docker compose up --build
```

### 4. Открыть приложение

```text
http://localhost:8001
```

---

## Локальный запуск без Docker

### 1. Установить зависимости

```bash
pip install -r requirements.txt
```

### 2. Поднять PostgreSQL

Создай базу данных и пропиши правильный `DATABASE_URL` в `config.py`.

### 3. Запустить проект

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

После запуска приложение будет доступно по адресу:

```text
http://localhost:8000
```

---

## Первый запуск

При первом запуске приложение:

* создаёт таблицы в базе
* создаёт суперадмина
* запускает планировщик уведомлений
* пытается поднять Telegram-бота, если указан `BOT_TOKEN`

---

## Логика уведомлений

Система напоминаний работает по нарастающей срочности:

* за 5–7 дней — мягкие напоминания
* за 3–5 дней — более настойчивые
* за 1–3 дня — усиленные
* менее чем за 24 часа — срочные
* после просрочки — регулярные уведомления о пропущенном дедлайне

---

## Особенности проекта

* Асинхронная архитектура
* Поддержка Telegram deep link для привязки аккаунта
* Работа с голосом через Gemini
* Разделение логики по модулям:

  * `routers/` — маршруты
  * `services/` — AI и планировщик
  * `models/` — база данных
  * `templates/` — HTML-шаблоны
* Готовность к запуску в Docker

---

## Что можно улучшить дальше

* вынести секреты в `.env`
* добавить Alembic для миграций
* добавить роли и права доступа
* сделать REST API для мобильного клиента
* подключить WebSocket вместо SSE
* добавить повторяющиеся задачи
* добавить загрузку файлов к задачам
* внедрить тесты

---

## Скриншоты
> <img width="1280" height="664" alt="image" src="https://github.com/user-attachments/assets/74522725-1672-4c63-bb6a-e0e72cf66171" />
> <img width="1280" height="664" alt="image" src="https://github.com/user-attachments/assets/7fede1fd-fdf2-41ee-9705-18e302b38084" />
><img width="1280" height="659" alt="image" src="https://github.com/user-attachments/assets/ff8a2327-c707-4b12-9eab-56499eb7a5c5" />
><img width="1280" height="670" alt="image" src="https://github.com/user-attachments/assets/3cf747b0-d08c-4ffa-aee2-480b4c4765a2" />
---

## Статус проекта

Проект находится в рабочем состоянии и уже включает:

* backend
* templates UI
* Telegram-бота
* AI-функции
* систему уведомлений
* Docker-конфигурацию

