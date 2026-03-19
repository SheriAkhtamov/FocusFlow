"""
AI-сервис: парсинг задач через Gemini + генерация уведомлений.
"""
import json
from datetime import datetime, timezone, timedelta
from google import genai
from google.genai import types

from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

SAFETY_SETTINGS = [
    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
]


async def parse_task_command(text: str) -> dict:
    """Превращает текст пользователя в JSON задачи."""
    TASHKENT_TZ = timezone(timedelta(hours=5))
    now = datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M")
    prompt = f"""Ты — парсер задач. Текущая дата и время: {now}.

Текст пользователя: "{text}"

Проанализируй текст и извлеки задачу. Верни ТОЛЬКО валидный JSON (без markdown):
{{
    "title": "краткое название задачи",
    "deadline": "YYYY-MM-DD HH:MM",
    "type": "task"
}}

Если дата не указана явно, предположи ближайшую логичную дату.
Если время не указано, поставь 23:59.
Отвечай ТОЛЬКО JSON, без пояснений."""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
        config=types.GenerateContentConfig(safety_settings=SAFETY_SETTINGS),
    )

    # Очистка ответа от markdown-обёрток
    raw = response.text.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1])

    return json.loads(raw)


async def transcribe_voice(audio_bytes: bytes, mime_type: str = "audio/ogg") -> str:
    """Транскрибирует голосовое сообщение через Gemini."""
    audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
    prompt_text = (
        "Транскрибируй это голосовое сообщение на русском языке. "
        "Верни ТОЛЬКО текст того, что сказал человек, без пояснений."
    )
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[prompt_text, audio_part],
        config=types.GenerateContentConfig(safety_settings=SAFETY_SETTINGS),
    )
    return response.text.strip()


async def generate_notification(task_title: str, days_left: float, deadline_str: str = "") -> str:
    """Генерирует уведомление с нужным уровнем настойчивости."""
    hours_left = days_left * 24
    minutes_left = hours_left * 60

    if days_left > 3:
        level_desc = "Вежливо и заботливо напомни о задаче. Будь дружелюбным помощником."
    elif 1 <= days_left <= 3:
        level_desc = "Настойчиво напомни. Подчеркни важность и срочность. Без грубости."
    elif 0 < days_left < 1:
        level_desc = "ОЧЕНЬ СРОЧНО! Пиши КАПСОМ. Скажи что нужно по быстрее закончить, времени мало, но БЕЗ оскорблений и матов. Тон: тревожный, настойчивый."
    else:
        level_desc = "Задача просрочена! Пиши КАПСОМ. Скажи что задача просрочена, но все равно нужно выполнить, но БЕЗ оскорблений и матов. Подчеркни, что срок уже прошёл."

    # Формируем инфо о времени
    if days_left < 0:
        time_info = f"Просрочено на {abs(hours_left):.0f} ч."
    elif hours_left < 1:
        time_info = f"До дедлайна осталось {minutes_left:.0f} минут"
    elif hours_left < 24:
        time_info = f"До дедлайна осталось {hours_left:.0f} ч."
    else:
        time_info = f"До дедлайна осталось {days_left:.1f} дн."

    deadline_info = f"\nДедлайн: {deadline_str}" if deadline_str else ""

    prompt = f"""Ты — вежливый персональный ассистент FocusFlow.
Задача: "{task_title}"{deadline_info}
{time_info}

Инструкция: {level_desc}

Обязательно укажи название задачи и оставшееся время (минуты, часы или дни) в уведомлении.
НИКОГДА не используй мат, оскорбления или грубость.
Напиши ОДНО уведомление для Telegram. Максимум 30 слов. Только текст сообщения, без кавычек."""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
        config=types.GenerateContentConfig(
            safety_settings=SAFETY_SETTINGS,
            temperature=0.7,
        ),
    )
    return response.text.strip()
