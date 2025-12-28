"""Точка входа сервиса уведомлений."""
import logging
from typing import Dict

from fastapi import Depends, FastAPI, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import NotificationLog
from .config import get_settings
from .dependencies import get_db_session
from .logging_config import configure_logging
from .schemas import (
    NotificationLogCreate,
    NotificationLogResponse,
    NotificationLogsList,
)

configure_logging()
settings = get_settings()
logger = logging.getLogger(settings.app_name)

app = FastAPI(
    title="Notification Service",
    version="0.1.0",
    description="Каркас сервиса уведомлений.",
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


@app.post("/notify/log", status_code=status.HTTP_202_ACCEPTED, response_model=Dict[str, str])
async def log_notification(
    payload: NotificationLogCreate,
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, str]:
    """
    Принимает событие, сохраняет в БД и пишет в stdout.

    Возвращает статус logged.
    """
    log_entry = NotificationLog(
        user_id=payload.user_id,
        event_type=payload.event_type,
        message=payload.message,
        payload=payload.payload,
    )
    session.add(log_entry)
    await session.commit()
    logger.info(
        "Принято событие %s для пользователя %s: %s",
        payload.event_type,
        payload.user_id,
        payload.message,
    )
    return {"status": "logged"}


@app.get("/notify/logs", response_model=NotificationLogsList)
async def get_logs(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(None, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> NotificationLogsList:
    """
    Возвращает список логов (для отладки).

    Пагинация: limit/offset. По умолчанию limit берется из настроек.
    """
    settings = get_settings()
    limit_val = limit or settings.default_page_size
    limit_val = min(limit_val, settings.max_page_size)

    stmt = (
        select(NotificationLog)
        .order_by(NotificationLog.created_at.desc())
        .limit(limit_val)
        .offset(offset)
    )
    result = await session.execute(stmt)
    logs = result.scalars().all()

    total_stmt = select(func.count()).select_from(NotificationLog)
    total = (await session.execute(total_stmt)).scalar_one()

    return NotificationLogsList(
        items=[
            NotificationLogResponse(
                id=log.id,
                user_id=str(log.user_id) if log.user_id else None,
                event_type=log.event_type,
                message=log.message,
                payload=log.payload,
                created_at=log.created_at,
            )
            for log in logs
        ],
        total=total,
        limit=limit_val,
        offset=offset,
    )
