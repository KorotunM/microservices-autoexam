"""Настройки логирования для сервиса."""
import logging

from .config import get_settings


def configure_logging() -> None:
    """
    Включает базовое логирование в stdout.

    Уровень и формат можно задать через переменные окружения:
    LOG_LEVEL и LOG_FORMAT.
    """
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format=settings.log_format,
        handlers=[logging.StreamHandler()],
    )
