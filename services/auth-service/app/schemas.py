"""Схемы запросов/ответов для auth-service."""
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """Тело запроса регистрации."""

    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=4, max_length=64, description="Пароль от 4 до 64 символов")


class RegisterResponse(BaseModel):
    """Ответ на успешную регистрацию."""

    user_id: str
    username: str


class LoginRequest(BaseModel):
    """Тело запроса логина."""

    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=4, max_length=64, description="Пароль от 4 до 64 символов")


class TokenResponse(BaseModel):
    """Ответ с JWT токеном."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ValidateResponse(BaseModel):
    """Ответ на валидацию токена."""

    user_id: str
    username: str
