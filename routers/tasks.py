"""
CRUD задач + Страницы: «Сегодня», Календарь, Настройки.
"""
import secrets
from datetime import datetime, timedelta, timezone
import calendar as cal_module

TASHKENT_TZ = timezone(timedelta(hours=5))
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db, User, Task
from routers.auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ---------- Главная — «Задачи» ----------

@router.get("/", response_class=HTMLResponse)
async def tasks_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(TASHKENT_TZ).replace(tzinfo=None)
    today_date = now.date()

    result = await db.execute(
        select(Task)
        .where(
            Task.user_id == current_user.id,
            Task.is_done == False,
        )
        .order_by(Task.deadline.asc())
    )
    all_tasks = result.scalars().all()

    # Группируем задачи по дням
    from collections import OrderedDict

    day_names = {
        0: "Понедельник", 1: "Вторник", 2: "Среда",
        3: "Четверг", 4: "Пятница", 5: "Суббота", 6: "Воскресенье",
    }
    month_names_gen = [
        "", "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря",
    ]

    overdue_tasks = []
    grouped: OrderedDict[str, dict] = OrderedDict()

    for t in all_tasks:
        hours_left = (t.deadline - now).total_seconds() / 3600
        task_date = t.deadline.date()

        if hours_left < 0:
            color, label = "red", "Просрочено"
        elif hours_left < 6:
            color, label = "red", "Горит!"
        elif hours_left < 24:
            color, label = "yellow", "Скоро"
        elif hours_left < 72:
            color, label = "yellow", "Через пару дней"
        else:
            color, label = "green", "Есть время"

        item = {"task": t, "color": color, "label": label, "hours_left": hours_left}

        # Просроченные — отдельная группа
        if task_date < today_date:
            overdue_tasks.append(item)
            continue

        # Определяем название группы
        diff_days = (task_date - today_date).days
        if diff_days == 0:
            group_key = task_date.isoformat()
            group_title = "Сегодня"
            group_subtitle = f"{task_date.day} {month_names_gen[task_date.month]}"
            group_accent = "indigo"
        elif diff_days == 1:
            group_key = task_date.isoformat()
            group_title = "Завтра"
            group_subtitle = f"{task_date.day} {month_names_gen[task_date.month]}, {day_names[task_date.weekday()]}"
            group_accent = "sky"
        else:
            group_key = task_date.isoformat()
            group_title = f"{task_date.day} {month_names_gen[task_date.month]}"
            group_subtitle = day_names[task_date.weekday()]
            group_accent = "slate"

        if group_key not in grouped:
            grouped[group_key] = {
                "title": group_title,
                "subtitle": group_subtitle,
                "accent": group_accent,
                "tasks": [],
            }
        grouped[group_key]["tasks"].append(item)

    total_count = len(all_tasks)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": current_user,
            "overdue_tasks": overdue_tasks,
            "grouped_tasks": grouped,
            "total_count": total_count,
            "now": now,
        },
    )


# ---------- Добавление задачи ----------

@router.post("/tasks/add")
async def add_task(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    deadline_date: str = Form(...),
    deadline_time: str = Form("23:59"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deadline = datetime.strptime(f"{deadline_date} {deadline_time}", "%Y-%m-%d %H:%M")
    task = Task(
        user_id=current_user.id,
        title=title,
        description=description,
        deadline=deadline,
    )
    db.add(task)
    await db.commit()
    return RedirectResponse(url="/", status_code=302)


# ---------- Пометить как выполненную ----------

@router.post("/tasks/{task_id}/done")
async def mark_done(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404)
    task.is_done = True
    await db.commit()
    return RedirectResponse(url="/", status_code=302)


# ---------- Удалить задачу ----------

@router.post("/tasks/{task_id}/delete")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404)
    await db.delete(task)
    await db.commit()
    return RedirectResponse(url="/", status_code=302)


# ---------- Календарь ----------

@router.get("/calendar", response_class=HTMLResponse)
async def calendar_page(
    request: Request,
    year: int = None,
    month: int = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(TASHKENT_TZ).replace(tzinfo=None)
    year = year or now.year
    month = month or now.month

    _, days_in_month = cal_module.monthrange(year, month)

    # Задачи в этом месяце
    month_start = datetime(year, month, 1)
    month_end = datetime(year, month, days_in_month, 23, 59, 59) + timedelta(seconds=1)
    result = await db.execute(
        select(Task).where(
            Task.user_id == current_user.id,
            Task.deadline >= month_start,
            Task.deadline < month_end,
        )
    )
    tasks = result.scalars().all()

    # Подсчёт задач по дням
    day_counts = {}
    day_colors = {}
    for t in tasks:
        d = t.deadline.date()
        day_counts[d] = day_counts.get(d, 0) + 1
        hours_left = (t.deadline - now).total_seconds() / 3600
        if hours_left < 0 or hours_left < 24:
            day_colors[d] = "red"
        elif hours_left < 72 and day_colors.get(d) != "red":
            day_colors[d] = "yellow"
        elif d not in day_colors:
            day_colors[d] = "green"

    # Формирование недель для шаблона
    cal = cal_module.Calendar(firstweekday=0)
    weeks = cal.monthdatescalendar(year, month)

    # Навигация
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    month_names = [
        "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
    ]

    return templates.TemplateResponse(
        "calendar.html",
        {
            "request": request,
            "user": current_user,
            "weeks": weeks,
            "year": year,
            "month": month,
            "month_name": month_names[month],
            "day_counts": day_counts,
            "day_colors": day_colors,
            "today": now.date(),
            "prev_year": prev_year,
            "prev_month": prev_month,
            "next_year": next_year,
            "next_month": next_month,
        },
    )


# ---------- Задачи за конкретный день ----------

@router.get("/calendar/{day_str}", response_class=HTMLResponse)
async def calendar_day(
    day_str: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    day = datetime.strptime(day_str, "%Y-%m-%d").date()
    day_start = datetime(day.year, day.month, day.day)
    day_end = day_start + timedelta(days=1)

    result = await db.execute(
        select(Task).where(
            Task.user_id == current_user.id,
            Task.deadline >= day_start,
            Task.deadline < day_end,
        ).order_by(Task.deadline.asc())
    )
    tasks = result.scalars().all()

    now = datetime.now(TASHKENT_TZ).replace(tzinfo=None)
    tasks_with_status = []
    for t in tasks:
        hours_left = (t.deadline - now).total_seconds() / 3600
        if hours_left < 0:
            color = "red"
            label = "Просрочено"
        elif hours_left < 24:
            color = "red"
            label = "Горит!"
        elif hours_left < 72:
            color = "yellow"
            label = "Скоро"
        else:
            color = "green"
            label = "Есть время"
        tasks_with_status.append({"task": t, "color": color, "label": label})

    return templates.TemplateResponse(
        "day_tasks.html",
        {
            "request": request,
            "user": current_user,
            "tasks": tasks_with_status,
            "day": day,
        },
    )


# ---------- Настройки ----------

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Генерируем токен привязки, если нет
    if not current_user.telegram_link_token:
        current_user.telegram_link_token = secrets.token_urlsafe(32)
        await db.commit()

    bot_username = None
    try:
        from bot import bot as tg_bot
        me = await tg_bot.get_me()
        bot_username = me.username
    except Exception:
        bot_username = "YourBotUsername"

    telegram_link = f"https://t.me/{bot_username}?start={current_user.telegram_link_token}"

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "user": current_user,
            "telegram_link": telegram_link,
            "telegram_connected": current_user.telegram_id is not None,
        },
    )
