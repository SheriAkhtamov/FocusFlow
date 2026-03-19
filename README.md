# FocusFlow

**FocusFlow** — это умный менеджер задач с AI-напоминаниями, веб-интерфейсом и Telegram-ботом.  
Проект позволяет создавать задачи вручную, текстом через AI или голосом, отслеживать дедлайны в календаре и получать уведомления по мере приближения срока.

> Внутреннее имя проекта в отчёте: `brain_fucker`  
> Основное название приложения в коде и интерфейсе: **FocusFlow**

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