"""Тесты notification-service: логирование и получение логов."""
import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

ROOT_DIR = Path(__file__).resolve().parents[3]
SERVICE_DIR = Path(__file__).resolve().parents[1]
for p in (ROOT_DIR, SERVICE_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import db.session as db_session  # noqa: E402
from db.models import Base  # noqa: E402
from app.main import app  # noqa: E402


@asynccontextmanager
async def override_db(url: str) -> AsyncGenerator[None, None]:
    """Подменяет движок/сессии на тестовые."""
    original_engine: AsyncEngine = db_session.engine
    original_factory = db_session.SessionFactory

    test_engine = create_async_engine(url, future=True)
    db_session.SessionFactory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    db_session.engine = test_engine

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield
    finally:
        db_session.SessionFactory = original_factory
        db_session.engine = original_engine
        await test_engine.dispose()


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Создает тестовый клиент с временной БД."""
    test_db_url = "sqlite+aiosqlite:///:memory:"
    os.environ["DATABASE_URL"] = test_db_url

    loop = asyncio.get_event_loop()
    ctx = override_db(test_db_url)
    loop.run_until_complete(ctx.__aenter__())

    with TestClient(app) as c:
        yield c

    loop.run_until_complete(ctx.__aexit__(None, None, None))


def test_log_and_list(client: TestClient) -> None:
    """Проверяет POST /notify/log и GET /notify/logs."""
    payload = {
        "user_id": None,
        "event_type": "test_event",
        "message": "Hello",
        "payload": {"key": "value"},
    }
    resp = client.post("/notify/log", json=payload)
    assert resp.status_code == 202, resp.text
    assert resp.json()["status"] == "logged"

    resp_list = client.get("/notify/logs")
    assert resp_list.status_code == 200, resp_list.text
    data = resp_list.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    assert data["items"][0]["event_type"] == "test_event"
