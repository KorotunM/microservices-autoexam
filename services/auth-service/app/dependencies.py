from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from .security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


async def get_db_session() -> AsyncSession:
    async for session in get_session():
        return session


async def get_current_user_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Отсутствует Bearer токен",
        )
    try:
        return decode_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или истекший токен",
        ) from None
