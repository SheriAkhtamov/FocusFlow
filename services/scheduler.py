"""
APScheduler: проверка дедлайнов и отправка эскалирующих уведомлений.
Стратегия «7-дневной осады». Доставка: Telegram + SSE (веб).
"""
import logging
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

TASHKENT_TZ = timezone(timedelta(hours=5))

from models.database import async_session, Task, User

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def _should_notify(task: Task, now: datetime) -> tuple[str | None, float]:
    """
    Определяет нужно ли отправлять уведомление.
    Возвращает (mode, days_left) или (None, 0).
    """
    time_left = task.deadline - now
    total_seconds = time_left.total_seconds()
    hours_left = total_seconds / 3600
    days_left = total_seconds / 86400

    # Уже напоминали недавно?
    if task.last_reminded_at:
        since_last = (now - task.last_reminded_at).total_seconds()
    else:
        since_last = float("inf")

    # ---------- Просрочено ----------
    if hours_left < 0:
        if since_last >= 900:  # каждые 15 мин
            return "humiliation", days_left
        return None, 0

    # ---------- < 6 часов — срочный режим ----------
    if hours_left <= 6:
        if since_last >= 3600:  # каждый час
            return "aggressive", days_left
        return None, 0

    # ---------- < 24 часов — агрессия ----------
    if hours_left <= 24:
        if since_last >= 10800:  # каждые 3 часа
            return "aggressive", days_left
        return None, 0

    # ---------- 1–3 дня — сарказм ----------
    if days_left <= 3:
        if since_last >= 28800:  # каждые 8 часов
            return "passive_aggressive", days_left
        return None, 0

    # ---------- 3–5 дней — мягкое давление ----------
    if days_left <= 5:
        if since_last >= 43200:  # каждые 12 часов
            return "passive_aggressive", days_left
        return None, 0

    # ---------- 5–7 дней — заботливое напоминание ----------
    if days_left <= 7:
        if since_last >= 86400:  # раз в день
            return "gentle", days_left
        return None, 0

    return None, 0


LEVEL_TO_INT = {
    "gentle": 0,
    "passive_aggressive": 2,
    "aggressive": 3,
    "humiliation": 5,
}


async def dispatch_notification(user: User, task: Task, message: str, level: str):
    """Отправляет уведомление по ОБОИМ каналам: SSE (веб) + Telegram."""
    from routers.notifications import send_web_notification

    # 1. Веб (SSE) — всегда пытаемся
    await send_web_notification(user.id, task.title, message, level)

    # 2. Telegram — только если chat_id привязан
    if user.telegram_id:
        try:
            from bot import send_notification
            await send_notification(user.telegram_id, message)
        except Exception as e:
            logger.error(f"Telegram send failed for user {user.username}: {e}")


async def check_deadlines():
    """Основной тик планировщика — запускается каждую минуту."""
    from services.ai_service import generate_notification

    now = datetime.now(TASHKENT_TZ).replace(tzinfo=None)

    async with async_session() as session:
        result = await session.execute(
            select(Task, User)
            .join(User, Task.user_id == User.id)
            .where(Task.is_done == False)
        )
        rows = result.all()

        for task, user in rows:
            # Пропускаем пользователей без Telegram и без веб-подключения
            from routers.notifications import notification_queues
            has_web = user.id in notification_queues
            has_telegram = user.telegram_id is not None
            if not has_web and not has_telegram:
                continue

            mode, days_left = _should_notify(task, now)
            if mode is None:
                continue

            try:
                deadline_str = task.deadline.strftime('%d.%m.%Y %H:%M')
                text = await generate_notification(task.title, days_left, deadline_str)
                await dispatch_notification(user, task, text, mode)

                task.last_reminded_at = now
                task.reminder_level = LEVEL_TO_INT.get(mode, 0)
                await session.commit()

                logger.info(f"[{mode}] → {user.username}: {text[:60]}...")
            except Exception as e:
                logger.error(f"Ошибка при обработке задачи {task.id}: {e}")


def start_scheduler():
    """Запуск планировщика."""
    scheduler.add_job(check_deadlines, "interval", minutes=1, id="check_deadlines")
    scheduler.start()
    logger.info("APScheduler запущен (тик каждую минуту)")


def stop_scheduler():
    """Остановка планировщика."""
    scheduler.shutdown()
