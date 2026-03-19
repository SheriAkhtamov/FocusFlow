"""
API роутер: парсинг задачи через AI + голосовой ввод.
"""
from fastapi import APIRouter, Request, Depends, UploadFile, File
from fastapi.responses import JSONResponse

from models.database import User
from routers.auth import get_current_user
from services.ai_service import parse_task_command, transcribe_voice

router = APIRouter(prefix="/api")


@router.post("/parse_task")
async def parse_task(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Принимает текст, возвращает распарсенную задачу."""
    body = await request.json()
    text = body.get("text", "")
    if not text:
        return JSONResponse({"error": "Текст не может быть пустым"}, status_code=400)

    try:
        parsed = await parse_task_command(text)
        return JSONResponse(parsed)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/voice_task")
async def voice_task(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Принимает аудио, транскрибирует через Gemini, парсит задачу."""
    try:
        audio_bytes = await audio.read()
        mime = audio.content_type or "audio/webm"

        transcript = await transcribe_voice(audio_bytes, mime)
        if not transcript:
            return JSONResponse({"error": "Не удалось распознать речь"}, status_code=400)

        parsed = await parse_task_command(transcript)
        parsed["transcript"] = transcript
        return JSONResponse(parsed)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
