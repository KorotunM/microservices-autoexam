"""Точка входа сервиса авторизации."""
import logging
from typing import Dict

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User
from .config import get_settings
from .dependencies import get_current_user_token, get_db_session
from .logging_config import configure_logging
from .schemas import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    ValidateResponse,
)
from .security import create_access_token, hash_password, verify_password

configure_logging()
settings = get_settings()
logger = logging.getLogger(settings.app_name)

app = FastAPI(
    title="Auth Service",
    version="0.1.0",
    description="Каркас сервиса авторизации.",
)


@app.get("/health/live")
async def health_live() -> Dict[str, str]:
    """Эндпоинт для проверки, что процесс живой."""
    return {"status": "live"}


@app.get("/health/ready")
async def health_ready() -> Dict[str, str]:
    """Эндпоинт для проверки готовности приложения."""
    return {"status": "ready"}


@app.on_event("startup")
async def on_startup() -> None:
    """Выводит информацию при старте сервиса."""
    logger.info(
        "Сервис %s запущен на %s:%s с БД %s",
        settings.app_name,
        settings.host,
        settings.port,
        settings.database_url,
    )


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Финализирует работу сервиса."""
    logger.info("Сервис %s завершает работу", settings.app_name)


@app.post(
    "/auth/register",
    status_code=status.HTTP_201_CREATED,
    response_model=RegisterResponse,
)
async def register_user(
    payload: RegisterRequest, session: AsyncSession = Depends(get_db_session)
) -> RegisterResponse:
    """
    Регистрирует нового пользователя.

    Возвращает 409 если username занят.
    """
    user = User(username=payload.username, password_hash=hash_password(payload.password))
    session.add(user)
    try:
        await session.commit()
        await session.refresh(user)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Имя пользователя уже занято",
        )

    return RegisterResponse(user_id=str(user.id), username=user.username)


@app.post("/auth/login", response_model=TokenResponse)
async def login_user(
    payload: LoginRequest, session: AsyncSession = Depends(get_db_session)
) -> TokenResponse:
    """
    Авторизация по логину и паролю, возвращает JWT.

    При неверном пароле/пользователе возвращает 401.
    """
    stmt = select(User).where(User.username == payload.username)
    result = await session.execute(stmt)
    user: User | None = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )

    token_data = create_access_token(user_id=str(user.id), username=user.username)
    return TokenResponse(
        access_token=token_data["token"],
        expires_in=token_data["expires_in"],
    )


@app.get("/auth/validate", response_model=ValidateResponse)
async def validate_token(
    token_payload: dict = Depends(get_current_user_token),
) -> ValidateResponse:
    """
    Проверяет переданный Bearer JWT и возвращает payload пользователя.

    Токен передается через Authorization: Bearer <token>.
    """
    return ValidateResponse(
        user_id=token_payload["sub"],
        username=token_payload["username"],
    )
