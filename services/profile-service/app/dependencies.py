from typing import Annotated, Dict

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from .config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


async def get_db_session() -> AsyncSession:
    async for session in get_session():
        return session


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]
) -> Dict[str, str]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Отсутствует Bearer токен",
        )

    settings = get_settings()
    headers = {"Authorization": f"Bearer {credentials.credentials}"}
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(settings.auth_validate_url, headers=headers)
        except httpx.HTTPError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Ошибка проверки токена",
            ) from None

    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
        )

    data = resp.json()
    return {"user_id": data.get("user_id"), "username": data.get("username")}
