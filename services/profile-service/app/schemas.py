"""Схемы запросов/ответов профиля."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class ProfileResponse(BaseModel):
    """Ответ с данными профиля."""

    user_id: str
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    created_at: datetime
    updated_at: datetime


class ProfileUpdateRequest(BaseModel):
    """Запрос на обновление профиля."""

    full_name: Optional[str] = Field(None, max_length=128)
    email: Optional[EmailStr] = None
