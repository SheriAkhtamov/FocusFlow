# FocusFlow

**FocusFlow** — это умный менеджер задач с AI-напоминаниями, веб-интерфейсом и Telegram-ботом.  
Проект позволяет создавать задачи вручную, текстом через AI или голосом, отслеживать дедлайны в календаре и получать уведомления по мере приближения срока.

> <img width="1280" height="664" alt="image" src="https://github.com/user-attachments/assets/74522725-1672-4c63-bb6a-e0e72cf66171" />
> <img width="1280" height="664" alt="image" src="https://github.com/user-attachments/assets/7fede1fd-fdf2-41ee-9705-18e302b38084" />
><img width="1280" height="659" alt="image" src="https://github.com/user-attachments/assets/ff8a2327-c707-4b12-9eab-56499eb7a5c5" />
><img width="1280" height="670" alt="image" src="https://github.com/user-attachments/assets/3cf747b0-d08c-4ffa-aee2-480b4c4765a2" />
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
