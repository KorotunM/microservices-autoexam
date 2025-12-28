"""Схемы запросов/ответов для сервиса уведомлений."""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class NotificationLogCreate(BaseModel):
    """Запрос на логирование события."""

    user_id: Optional[str] = Field(None, description="UUID пользователя, может быть пустым")
    event_type: str = Field("event", max_length=64)
    message: str = Field(..., min_length=1)
    payload: Optional[Dict[str, Any]] = None


class NotificationLogResponse(BaseModel):
    """Ответ с данными записи лога."""

    id: int
    user_id: Optional[str]
    event_type: str
    message: str
    payload: Optional[Dict[str, Any]]
    created_at: datetime


class NotificationLogsList(BaseModel):
    """Список логов с пагинацией."""

    items: list[NotificationLogResponse]
    total: int
    limit: int
    offset: int
