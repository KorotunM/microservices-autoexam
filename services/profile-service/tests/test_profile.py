"""Интеграционные тесты profile-service с моками auth-service."""
import asyncio
import os
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response
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
    """Создает тестовый клиент с временной БД и моком auth-service."""
    test_db_url = "sqlite+aiosqlite:///:memory:"
    os.environ["DATABASE_URL"] = test_db_url

    loop = asyncio.get_event_loop()
    ctx = override_db(test_db_url)
    loop.run_until_complete(ctx.__aenter__())

    with respx.mock(assert_all_called=False) as router:
        with TestClient(app) as c:
            yield c, router

    loop.run_until_complete(ctx.__aexit__(None, None, None))


def _mock_auth(router: respx.Router, user_id: str, username: str, status_code: int = 200) -> None:
    """Добавляет мок ответа auth-service /auth/validate."""
    router.get("http://auth-service:8001/auth/validate").mock(
        return_value=Response(status_code=status_code, json={"user_id": user_id, "username": username}),
    )


def test_get_profile_creates_default(client: tuple[TestClient, respx.Router]) -> None:
    """GET /profile/me создаёт профиль, если его нет."""
    test_client, router = client
    user_id = str(uuid.uuid4())
    _mock_auth(router, user_id, "alice")

    resp = test_client.get("/profile/me", headers={"Authorization": "Bearer token"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["user_id"] == user_id
    assert data["full_name"] is None
    assert data["email"] is None


def test_update_profile(client: tuple[TestClient, respx.Router]) -> None:
    """PUT /profile/me обновляет поля профиля."""
    test_client, router = client
    user_id = str(uuid.uuid4())
    _mock_auth(router, user_id, "bob")

    # Создадим профиль чтением
    resp_get = test_client.get("/profile/me", headers={"Authorization": "Bearer token"})
    assert resp_get.status_code == 200

    resp = test_client.put(
        "/profile/me",
        json={"full_name": "Bob Builder", "email": "bob@example.com"},
        headers={"Authorization": "Bearer token"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["full_name"] == "Bob Builder"
    assert data["email"] == "bob@example.com"


def test_unauthorized(client: tuple[TestClient, respx.Router]) -> None:
    """Возврат 401 при недействительном токене."""
    test_client, router = client
    user_id = str(uuid.uuid4())
    _mock_auth(router, user_id, "charlie", status_code=401)

    resp = test_client.get("/profile/me", headers={"Authorization": "Bearer token"})
    assert resp.status_code == 401
