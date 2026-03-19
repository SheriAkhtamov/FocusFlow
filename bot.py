"""
Telegram-бот (aiogram 3.x): привязка аккаунта, меню, добавление задач голосом.
"""
import logging
from datetime import datetime, timezone, timedelta

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    BotCommand,
)
from aiogram.filters import CommandStart, CommandObject, Command
from sqlalchemy import select

from config import BOT_TOKEN
from models.database import async_session, User, Task

logger = logging.getLogger(__name__)

TASHKENT_TZ = timezone(timedelta(hours=5))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ---------- Клавиатуры ----------

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📋 Меню")]],
    resize_keyboard=True,
)

MENU_INLINE = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📅 Сегодняшние задачи", callback_data="today_tasks")],
    [InlineKeyboardButton(text="➕ Добавить новую задачу", callback_data="add_task")],
])


async def _get_user_by_tg(tg_id: int) -> User | None:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == tg_id)
        )
        return result.scalar_one_or_none()


# ---------- /start с токеном ----------

@router.message(CommandStart(deep_link=True))
async def cmd_start_with_token(message: Message, command: CommandObject):
    """Обработка /start с токеном привязки."""
    token = command.args
    if not token:
        await message.answer("❌ Токен не указан. Перейдите по ссылке из настроек приложения.")
        return

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_link_token == token)
        )
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("❌ Недействительный токен. Попробуйте получить новую ссылку.")
            return

        user.telegram_id = message.from_user.id
        user.telegram_link_token = None
        await session.commit()

    await message.answer(
        f"✅ Аккаунт привязан! Привет, {user.username}!\n\n"
        "Теперь я буду напоминать тебе о задачах и встречах. "
        "Чем ближе дедлайн — тем настойчивее напоминания. ⏰\n\n"
        "Нажми «📋 Меню» чтобы начать.",
        reply_markup=MAIN_KEYBOARD,
    )


# ---------- /start обычный ----------

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработка обычного /start без токена."""
    user = await _get_user_by_tg(message.from_user.id)
    if user:
        await message.answer(
            f"✨ С возвращением, {user.username}!\n"
            "Нажми «📋 Меню» чтобы управлять задачами.",
            reply_markup=MAIN_KEYBOARD,
        )
    else:
        await message.answer(
            "✨ FocusFlow Bot\n\n"
            "Чтобы привязать аккаунт, перейдите по ссылке из настроек приложения.\n"
            "Я буду присылать вам напоминания о задачах и встречах.",
            reply_markup=MAIN_KEYBOARD,
        )


# ---------- Кнопка «Меню» ----------

@router.message(F.text == "📋 Меню")
async def show_menu(message: Message):
    user = await _get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("⚠️ Аккаунт не привязан. Перейдите по ссылке из настроек приложения.")
        return
    await message.answer("Выберите действие:", reply_markup=MENU_INLINE)


# ---------- Callback: Сегодняшние задачи ----------

@router.callback_query(F.data == "today_tasks")
async def cb_today_tasks(callback: CallbackQuery):
    await callback.answer()
    user = await _get_user_by_tg(callback.from_user.id)
    if not user:
        await callback.message.answer("⚠️ Аккаунт не привязан.")
        return

    now = datetime.now(TASHKENT_TZ).replace(tzinfo=None)

    async with async_session() as session:
        result = await session.execute(
            select(Task)
            .where(Task.user_id == user.id, Task.is_done == False)
            .order_by(Task.deadline.asc())
        )
        tasks = result.scalars().all()

    if not tasks:
        await callback.message.answer("🎉 У вас нет активных задач! Отдыхайте.")
        return

    lines = [f"📅 *Ваши задачи* ({len(tasks)}):\n"]
    for i, t in enumerate(tasks, 1):
        hours_left = (t.deadline - now).total_seconds() / 3600
        deadline_str = t.deadline.strftime("%d.%m %H:%M")
        if hours_left < 0:
            status = "🔴 просрочено"
        elif hours_left < 24:
            status = f"🟠 {hours_left:.0f}ч"
        elif hours_left < 72:
            status = f"🟡 {hours_left / 24:.0f}дн"
        else:
            status = f"🟢 {hours_left / 24:.0f}дн"
        lines.append(f"{i}. *{t.title}*\n   ⏰ {deadline_str} · {status}")

    await callback.message.answer("\n".join(lines), parse_mode="Markdown")


# ---------- Callback: Добавить задачу ----------

# Простое хранилище состояния (user_id -> "waiting_voice")
_waiting_for_voice: set[int] = set()

@router.callback_query(F.data == "add_task")
async def cb_add_task(callback: CallbackQuery):
    await callback.answer()
    user = await _get_user_by_tg(callback.from_user.id)
    if not user:
        await callback.message.answer("⚠️ Аккаунт не привязан.")
        return

    _waiting_for_voice.add(callback.from_user.id)
    await callback.message.answer(
        "🎤 *Отправьте голосовое сообщение* с описанием задачи.\n\n"
        "Например: _«Сдать отчёт в пятницу к шести вечера»_\n\n"
        "AI распознает речь и создаст задачу автоматически.",
        parse_mode="Markdown",
    )


# ---------- Обработка голосовых сообщений ----------

@router.message(F.voice)
async def handle_voice(message: Message):
    user = await _get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("⚠️ Аккаунт не привязан. Перейдите по ссылке из настроек приложения.")
        return

    # Убираем из ожидания
    _waiting_for_voice.discard(message.from_user.id)

    processing_msg = await message.answer("⏳ Распознаю голос и создаю задачу...")

    try:
        # 1. Скачиваем голосовое
        file = await bot.get_file(message.voice.file_id)
        from io import BytesIO
        buf = BytesIO()
        await bot.download_file(file.file_path, buf)
        audio_bytes = buf.getvalue()

        # 2. Транскрибируем через Gemini
        from services.ai_service import transcribe_voice, parse_task_command
        transcript = await transcribe_voice(audio_bytes, "audio/ogg")

        if not transcript:
            await processing_msg.edit_text("❌ Не удалось распознать речь. Попробуйте ещё раз.")
            return

        # 3. Парсим задачу через AI
        parsed = await parse_task_command(transcript)
        title = parsed.get("title", transcript)
        deadline_str = parsed.get("deadline", "")

        if not deadline_str:
            await processing_msg.edit_text(
                f"❌ Не удалось определить дедлайн.\n\n"
                f"Распознано: _{transcript}_",
                parse_mode="Markdown",
            )
            return

        deadline = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M")

        # 4. Сохраняем задачу
        async with async_session() as session:
            task = Task(
                user_id=user.id,
                title=title,
                deadline=deadline,
            )
            session.add(task)
            await session.commit()

        await processing_msg.edit_text(
            f"✅ *Задача создана!*\n\n"
            f"📝 {title}\n"
            f"⏰ {deadline.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"_Распознано: «{transcript}»_",
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(f"Ошибка обработки голоса: {e}")
        await processing_msg.edit_text(f"❌ Ошибка: {str(e)[:200]}")


# ---------- Отправка уведомлений ----------

async def send_notification(chat_id: int, text: str) -> bool:
    """Отправить уведомление пользователю."""
    try:
        await bot.send_message(chat_id=chat_id, text=text)
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки в Telegram (chat_id={chat_id}): {e}")
        return False


# ---------- Startup / Shutdown ----------

async def setup_bot_commands():
    """Установить команды бота в меню Telegram."""
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="menu", description="Открыть меню"),
    ])


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    """Обработка /menu."""
    user = await _get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("⚠️ Аккаунт не привязан. Перейдите по ссылке из настроек приложения.")
        return
    await message.answer("Выберите действие:", reply_markup=MENU_INLINE)


async def start_bot_polling():
    """Запуск бота в режиме polling."""
    logger.info("Telegram-бот запущен (polling)")
    await setup_bot_commands()
    await dp.start_polling(bot)


async def stop_bot():
    """Остановка бота."""
    await dp.stop_polling()
    await bot.session.close()
