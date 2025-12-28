"""Настройка AsyncEngine и фабрики сессий для сервисов."""
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@postgres:5432/autoexam",
)

# Создаем движок и фабрику сессий (используется в приложениях и Alembic)
engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False, future=True)
SessionFactory = async_sessionmaker(bind=engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Отдает сессию БД и автоматически возвращает соединение в пул."""
    async with SessionFactory() as session:
        yield session
