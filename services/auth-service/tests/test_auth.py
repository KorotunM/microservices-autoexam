"""Минимальные тесты для /auth/register, /auth/login, /auth/validate."""
import asyncio
import os
import sys
import uuid
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
    """
    Подменяет движок и фабрику сессий на тестовые.

    После тестов возвращает оригинальные значения.
    """
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
    """
    Создает тестовый клиент с временной БД.

    Используем sqlite in-memory для скорости (генерацию UUID задаем вручную).
    """
    test_db_url = "sqlite+aiosqlite:///:memory:"
    os.environ["DATABASE_URL"] = test_db_url

    loop = asyncio.get_event_loop()
    ctx = override_db(test_db_url)
    loop.run_until_complete(ctx.__aenter__())

    with TestClient(app) as c:
        yield c

    loop.run_until_complete(ctx.__aexit__(None, None, None))


def test_register_and_login_and_validate(client: TestClient) -> None:
    """Проверяет полный цикл: регистрация -> логин -> валидация токена."""
    username = f"user_{uuid.uuid4().hex[:8]}"
    password = "password123"

    # Регистрация
    resp = client.post("/auth/register", json={"username": username, "password": password})
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["username"] == username
    assert data["user_id"]

    # Повторная регистрация должна вернуть 409
    resp_dup = client.post("/auth/register", json={"username": username, "password": password})
    assert resp_dup.status_code == 409

    # Логин
    resp_login = client.post("/auth/login", json={"username": username, "password": password})
    assert resp_login.status_code == 200, resp_login.text
    token_data = resp_login.json()
    assert token_data["token_type"] == "bearer"
    assert token_data["access_token"]

    # Валидация
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    resp_valid = client.get("/auth/validate", headers=headers)
    assert resp_valid.status_code == 200, resp_valid.text
    valid_data = resp_valid.json()
    assert valid_data["username"] == username
