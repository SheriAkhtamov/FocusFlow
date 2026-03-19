"""
SSE-уведомления.
"""
import asyncio
import json
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse

from models.database import User
from routers.auth import get_current_user

router = APIRouter()
notification_queues: dict[int, asyncio.Queue] = {}

async def send_web_notification(user_id: int, task_title: str, message: str, level: str):
    """
    level: gentle | passive_aggressive | aggressive | humiliation
    """
    queue = notification_queues.get(user_id)
    if queue:
        payload = json.dumps({
            "title": task_title,
            "body": message,
            "level": level, 
        }, ensure_ascii=False)
        await queue.put(payload)

# Остальной код _sse_generator и notification_stream оставляем без изменений
async def _sse_generator(user_id: int, request: Request):
    queue = notification_queues.setdefault(user_id, asyncio.Queue())
    try:
        while True:
            if await request.is_disconnected():
                break
            try:
                message = await asyncio.wait_for(queue.get(), timeout=30)
                yield f"data: {message}\n\n"
            except asyncio.TimeoutError:
                yield ": ping\n\n"
    finally:
        notification_queues.pop(user_id, None)

@router.get("/api/notifications/stream")
async def notification_stream(request: Request, current_user: User = Depends(get_current_user)):
    return StreamingResponse(
        _sse_generator(current_user.id, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )