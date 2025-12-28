"""Простой фронтенд-сервер на FastAPI со SPA и прокси к внутренним сервисам."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

import httpx
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings

settings = get_settings()

def _resolve_log_level(value: str) -> int:
    """Возвращает числовой уровень логирования, по умолчанию INFO."""
    level_name = (value or "INFO").upper()
    return logging._nameToLevel.get(level_name, logging.INFO)

logging.basicConfig(
    level=_resolve_log_level(settings.log_level),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(settings.app_name)

app = FastAPI(title="Web Frontend", description="SPA для Autoexam", version="0.1.0")

# Путь к статике
static_dir = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")


def _frontend_index() -> FileResponse:
    """Возвращает основной HTML (SPA) для всех маршрутов."""
    return FileResponse(static_dir / "index.html")


def _auth_header(request: Request) -> Dict[str, str]:
    """Извлекает Authorization из исходного запроса."""
    auth = request.headers.get("Authorization")
    return {"Authorization": auth} if auth else {}


async def _proxy(
    method: str,
    url: str,
    request: Request,
    json_body: Any = None,
    params: Dict[str, Any] | None = None,
) -> Response:
    """
    Прозрачно проксирует запрос к внутреннему сервису.

    Передает Authorization и тело запроса, возвращает статус и JSON/текст дальше.
    """
    headers = _auth_header(request)
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.request(method, url, headers=headers, json=json_body, params=params)
        except httpx.HTTPError as exc:
            logger.error("Ошибка запроса к %s: %s", url, exc)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Сервис временно недоступен")

    content_type = resp.headers.get("content-type", "")
    if "application/json" in content_type:
        return JSONResponse(status_code=resp.status_code, content=resp.json())
    return Response(status_code=resp.status_code, content=resp.content, media_type=content_type)


@app.get("/health/live")
async def health_live() -> Dict[str, str]:
    """Показывает, что процесс живой."""
    return {"status": "live"}


@app.get("/health/ready")
async def health_ready() -> Dict[str, str]:
    """Показывает готовность приложения."""
    return {"status": "ready"}


@app.get("/ui-config.json")
async def ui_config() -> Dict[str, str]:
    """Возвращает конфигурационные тексты UI из env/ConfigMap."""
    return {
        "login_title": settings.login_title,
        "register_title": settings.register_title,
        "welcome_message": settings.welcome_message,
    }


# Прокси-эндпоинты к внутренним сервисам
@app.post("/api/auth/register")
async def api_register(request: Request) -> Response:
    body = await request.json()
    url = f"{settings.auth_base_url}/auth/register"
    return await _proxy("POST", url, request, json_body=body)


@app.post("/api/auth/login")
async def api_login(request: Request) -> Response:
    body = await request.json()
    url = f"{settings.auth_base_url}/auth/login"
    return await _proxy("POST", url, request, json_body=body)


@app.get("/api/profile/me")
async def api_profile_me(request: Request) -> Response:
    url = f"{settings.profile_base_url}/profile/me"
    return await _proxy("GET", url, request)


@app.put("/api/profile/me")
async def api_profile_update(request: Request) -> Response:
    body = await request.json()
    url = f"{settings.profile_base_url}/profile/me"
    return await _proxy("PUT", url, request, json_body=body)


@app.post("/api/finance/transactions")
async def api_finance_create(request: Request) -> Response:
    body = await request.json()
    url = f"{settings.finance_base_url}/finance/transactions"
    return await _proxy("POST", url, request, json_body=body)


@app.get("/api/finance/transactions")
async def api_finance_list(request: Request) -> Response:
    params = dict(request.query_params)
    url = f"{settings.finance_base_url}/finance/transactions"
    return await _proxy("GET", url, request, params=params)


@app.get("/api/finance/stats/summary")
async def api_finance_summary(request: Request) -> Response:
    url = f"{settings.finance_base_url}/finance/stats/summary"
    return await _proxy("GET", url, request)


@app.get("/api/finance/stats/by-category")
async def api_finance_by_category(request: Request) -> Response:
    url = f"{settings.finance_base_url}/finance/stats/by-category"
    return await _proxy("GET", url, request)


@app.get("/api/finance/stats/by-day")
async def api_finance_by_day(request: Request) -> Response:
    params = dict(request.query_params)
    url = f"{settings.finance_base_url}/finance/stats/by-day"
    return await _proxy("GET", url, request, params=params)


# SPA fallback: все остальные маршруты отдаем index.html
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str) -> FileResponse:  # noqa: ARG001
    """Возвращает SPA для любых путей, кроме /api и /static."""
    return _frontend_index()
