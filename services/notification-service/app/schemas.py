from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class NotificationLogCreate(BaseModel):

    user_id: Optional[str] = Field(None, description="UUID пользователя, может быть пустым")
    event_type: str = Field("event", max_length=64)
    message: str = Field(..., min_length=1)
    payload: Optional[Dict[str, Any]] = None


class NotificationLogResponse(BaseModel):

    id: int
    user_id: Optional[str]
    event_type: str
    message: str
    payload: Optional[Dict[str, Any]]
    created_at: datetime


class NotificationLogsList(BaseModel):

    items: list[NotificationLogResponse]
    total: int
    limit: int
    offset: int
