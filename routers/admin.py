"""
Админ-панель: управление пользователями.
"""
import secrets
import string
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db, User, Task, pwd_context
from routers.auth import get_current_user

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="templates")


def _generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _require_admin(user: User):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Только для администраторов")


# ---------- Список пользователей ----------

@router.get("/users", response_class=HTMLResponse)
async def users_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)

    result = await db.execute(
        select(User).order_by(User.id.asc())
    )
    all_users = result.scalars().all()

    # Подсчёт задач для каждого пользователя
    users_data = []
    for u in all_users:
        task_count_result = await db.execute(
            select(func.count(Task.id)).where(Task.user_id == u.id, Task.is_done == False)
        )
        task_count = task_count_result.scalar() or 0
        users_data.append({"user": u, "task_count": task_count})

    return templates.TemplateResponse(
        "admin_users.html",
        {
            "request": request,
            "user": current_user,
            "users_data": users_data,
            "created": None,
        },
    )


# ---------- Добавить пользователя ----------

@router.post("/users/add", response_class=HTMLResponse)
async def create_user(
    request: Request,
    new_username: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)

    existing = await db.execute(select(User).where(User.username == new_username))
    if existing.scalar_one_or_none():
        result = await db.execute(select(User).order_by(User.id.asc()))
        all_users = result.scalars().all()
        users_data = []
        for u in all_users:
            tc = await db.execute(
                select(func.count(Task.id)).where(Task.user_id == u.id, Task.is_done == False)
            )
            users_data.append({"user": u, "task_count": tc.scalar() or 0})
        return templates.TemplateResponse(
            "admin_users.html",
            {
                "request": request,
                "user": current_user,
                "users_data": users_data,
                "created": None,
                "error": f"Пользователь «{new_username}» уже существует",
            },
        )

    password = _generate_password()
    new_user = User(
        username=new_username,
        hashed_password=pwd_context.hash(password),
        is_admin=False,
    )
    db.add(new_user)
    await db.commit()

    result = await db.execute(select(User).order_by(User.id.asc()))
    all_users = result.scalars().all()
    users_data = []
    for u in all_users:
        tc = await db.execute(
            select(func.count(Task.id)).where(Task.user_id == u.id, Task.is_done == False)
        )
        users_data.append({"user": u, "task_count": tc.scalar() or 0})

    return templates.TemplateResponse(
        "admin_users.html",
        {
            "request": request,
            "user": current_user,
            "users_data": users_data,
            "created": {"username": new_username, "password": password},
        },
    )


# ---------- Удалить пользователя ----------

@router.post("/users/{user_id}/delete")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)

    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")

    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    await db.delete(target)
    await db.commit()
    return RedirectResponse(url="/admin/users", status_code=302)
