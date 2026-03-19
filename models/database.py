"""
SQLAlchemy Async модели и управление сессиями.
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, BigInteger, ForeignKey,
)
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, relationship
from passlib.context import CryptContext

from config import DATABASE_URL, SUPERADMIN_USERNAME, SUPERADMIN_PASSWORD

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    telegram_id = Column(BigInteger, nullable=True)
    telegram_link_token = Column(String(64), nullable=True, unique=True)
    is_admin = Column(Boolean, default=False)

    tasks = relationship("Task", back_populates="owner", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text, default="")
    deadline = Column(DateTime, nullable=False)
    is_done = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone(timedelta(hours=5))).replace(tzinfo=None))
    last_reminded_at = Column(DateTime, nullable=True)
    reminder_level = Column(Integer, default=0)

    owner = relationship("User", back_populates="tasks")


# ---------- Engine & Session ----------

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """FastAPI Dependency — выдаёт async-сессию."""
    async with async_session() as session:
        yield session


async def init_db():
    """Создание таблиц + суперадмин при первом запуске."""
    from sqlalchemy import select

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.username == SUPERADMIN_USERNAME)
        )
        if not result.scalar_one_or_none():
            admin = User(
                username=SUPERADMIN_USERNAME,
                hashed_password=pwd_context.hash(SUPERADMIN_PASSWORD),
                is_admin=True,
            )
            session.add(admin)
            await session.commit()
