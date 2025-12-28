from functools import lru_cache

from pydantic import BaseSettings, Field


class Settings(BaseSettings):

    app_name: str = Field("auth-service", env="APP_NAME")
    host: str = Field("0.0.0.0", env="APP_HOST")
    port: int = Field(8001, env="APP_PORT")
    database_url: str = Field(
        "postgresql+asyncpg://postgres:postgres@postgres:5432/autoexam",
        env="DATABASE_URL",
    )
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = Field(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s", env="LOG_FORMAT"
    )
    jwt_secret: str = Field("change-me", env="JWT_SECRET")
    jwt_ttl_seconds: int = Field(3600, env="JWT_TTL_SECONDS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
