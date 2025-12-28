"""Утилиты для хеширования паролей и выпуска JWT."""
import time
from typing import Any, Dict

import jwt
from fastapi import HTTPException, status
from passlib.context import CryptContext

from .config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Возвращает безопасный хеш пароля (bcrypt) с проверкой длины."""
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Пароль слишком длинный",
        )
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Проверяет пароль против хеша."""
    return pwd_context.verify(password, hashed_password)


def create_access_token(*, user_id: str, username: str) -> Dict[str, Any]:
    """
    Создает JWT токен с полями sub, username, iat, exp.

    Секрет и TTL берутся из настроек (env JWT_SECRET, JWT_TTL_SECONDS).
    """
    settings = get_settings()
    now = int(time.time())
    exp = now + settings.jwt_ttl_seconds
    payload: Dict[str, Any] = {
        "sub": user_id,
        "username": username,
        "iat": now,
        "exp": exp,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return {"token": token, "expires_in": settings.jwt_ttl_seconds}


def decode_token(token: str) -> Dict[str, Any]:
    """Декодирует и валидирует JWT, выбрасывает исключение при ошибке."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
