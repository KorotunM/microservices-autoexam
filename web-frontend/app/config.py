"""Настройки фронтенд-сервера и текстов интерфейса."""
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Базовые настройки FastAPI фронта и адресов внутренних сервисов."""

    app_name: str = Field("web-frontend", env="APP_NAME")
    host: str = Field("0.0.0.0", env="APP_HOST")
    port: int = Field(8080, env="APP_PORT")

    auth_base_url: str = Field("http://auth-service:8001", env="AUTH_BASE_URL")
    profile_base_url: str = Field("http://profile-service:8002", env="PROFILE_BASE_URL")
    finance_base_url: str = Field("http://finance-service:8003", env="FINANCE_BASE_URL")

    log_level: str = Field("INFO", env="LOG_LEVEL")

    login_title: str = Field("Вход в систему", env="LOGIN_TITLE")
    register_title: str = Field("Создайте аккаунт", env="REGISTER_TITLE")
    welcome_message: str = Field("Добро пожаловать", env="WELCOME_MESSAGE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
