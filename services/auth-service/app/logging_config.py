import logging

from .config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format=settings.log_format,
        handlers=[logging.StreamHandler()],
    )
