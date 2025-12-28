"""Точка входа сервиса профилей."""
import logging
from typing import Dict

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Profile
from .config import get_settings
from .dependencies import get_current_user, get_db_session
from .logging_config import configure_logging
from .schemas import ProfileResponse, ProfileUpdateRequest

configure_logging()
settings = get_settings()
logger = logging.getLogger(settings.app_name)

app = FastAPI(
    title="Profile Service",
    version="0.1.0",
    description="Каркас сервиса профилей.",
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


@app.get("/profile/me", response_model=ProfileResponse)
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ProfileResponse:
    """
    Возвращает профиль текущего пользователя.

    Если профиля нет — создаёт пустой профиль и возвращает его.
    """
    try:
        stmt = select(Profile).where(Profile.user_id == current_user["user_id"])
        result = await session.execute(stmt)
        profile: Profile | None = result.scalar_one_or_none()

        if profile is None:
            profile = Profile(user_id=current_user["user_id"])
            session.add(profile)
            await session.commit()
            await session.refresh(profile)

        return ProfileResponse(
            user_id=str(profile.user_id),
            username=current_user["username"],
            full_name=profile.full_name,
            email=profile.email,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
    except HTTPException:
        raise
    except Exception as exc:
        # Логируем неожиданные ошибки для быстрой диагностики 500
        logger.error("Ошибка при получении профиля пользователя", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось загрузить профиль",
        ) from exc


@app.put("/profile/me", response_model=ProfileResponse)
async def update_my_profile(
    payload: ProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ProfileResponse:
    """
    Обновляет профиль текущего пользователя.

    Возвращает обновлённые данные. Обрабатывает уникальность email.
    """
    stmt = select(Profile).where(Profile.user_id == current_user["user_id"])
    result = await session.execute(stmt)
    profile: Profile | None = result.scalar_one_or_none()

    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль не найден")

    values = {}
    if payload.full_name is not None:
        values["full_name"] = payload.full_name
    if payload.email is not None:
        values["email"] = payload.email

    if values:
        values["updated_at"] = func.now()
        stmt_update = (
            update(Profile)
            .where(Profile.user_id == current_user["user_id"])
            .values(**values)
        )
        try:
            await session.execute(stmt_update)
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="email уже используется",
            )
        except Exception:
            await session.rollback()
            raise
        # перечитываем профиль после обновления
        result = await session.execute(stmt)
        profile = result.scalar_one()

    return ProfileResponse(
        user_id=str(profile.user_id),
        username=current_user["username"],
        full_name=profile.full_name,
        email=profile.email,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
