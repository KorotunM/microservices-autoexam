"""
Настройки сервиса профилей.
Все значения можно переопределить через переменные окружения.
"""
from functools import lru_cache

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Базовые настройки приложения."""

    app_name: str = Field("profile-service", env="APP_NAME")
    host: str = Field("0.0.0.0", env="APP_HOST")
    port: int = Field(8002, env="APP_PORT")
    database_url: str = Field(
        "postgresql+asyncpg://postgres:postgres@postgres:5432/autoexam",
        env="DATABASE_URL",
    )
    auth_validate_url: str = Field(
        "http://auth-service:8001/auth/validate",
        env="AUTH_VALIDATE_URL",
    )
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = Field(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s", env="LOG_FORMAT"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Возвращает настроенный экземпляр настроек с кэшированием."""
    return Settings()
