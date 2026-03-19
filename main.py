"""
FocusFlow Task Manager — Точка входа.
FastAPI + APScheduler + Telegram Bot.
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from models.database import init_db
from routers import auth, tasks, api, admin, notifications
from routers.auth import RequiresLoginException
from services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Telegram bot polling task
bot_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / Shutdown."""
    global bot_task

    # --- Startup ---
    logger.info("✨ FocusFlow запускается...")
    await init_db()
    logger.info("✅ База данных инициализирована")

    start_scheduler()
    logger.info("✅ Планировщик запущен")

    # Запуск Telegram-бота в фоне (если токен настроен)
    try:
        from config import BOT_TOKEN
        if BOT_TOKEN and BOT_TOKEN != "your_telegram_bot_token":
            from bot import start_bot_polling
            bot_task = asyncio.create_task(start_bot_polling())
            logger.info("✅ Telegram-бот запущен")
        else:
            logger.warning("⚠️ BOT_TOKEN не настроен — бот не запущен")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")

    logger.info("🚀 FocusFlow готов к работе!")

    yield

    # --- Shutdown ---
    logger.info("🛑 FocusFlow останавливается...")
    stop_scheduler()
    if bot_task:
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass
    logger.info("👋 До встречи!")


# --- App ---
app = FastAPI(
    title="FocusFlow",
    description="Умный менеджер задач с AI-напоминаниями",
    lifespan=lifespan,
)


# --- Exception handler: redirect to login ---
@app.exception_handler(RequiresLoginException)
async def requires_login_handler(request: Request, exc: RequiresLoginException):
    return RedirectResponse(url="/login", status_code=302)


# --- Auth Middleware ---
class AuthRedirectMiddleware(BaseHTTPMiddleware):
    """Перенаправляет неавторизованных на /login."""
    OPEN_PATHS = {"/login", "/logout", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.OPEN_PATHS or request.url.path.startswith("/api/"):
            return await call_next(request)

        token = request.cookies.get("access_token")
        if not token and request.url.path != "/login":
            return RedirectResponse(url="/login", status_code=302)

        return await call_next(request)


app.add_middleware(AuthRedirectMiddleware)

# --- Routers ---
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(tasks.router)
app.include_router(api.router)
app.include_router(notifications.router)

