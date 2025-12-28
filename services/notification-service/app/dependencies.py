"""Зависимости FastAPI для доступа к БД."""
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session


async def get_db_session() -> AsyncSession:
    """Возвращает асинхронную сессию БД."""
    async for session in get_session():
        return session
