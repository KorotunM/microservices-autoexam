"""Точка входа сервиса финансов."""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Transaction
from .config import get_settings
from .dependencies import get_current_user, get_db_session
from .logging_config import configure_logging
from .schemas import (
    CategoryStatsResponse,
    DayStatsItem,
    DayStatsResponse,
    SummaryResponse,
    TransactionCreate,
    TransactionResponse,
    TransactionsListResponse,
)

configure_logging()
settings = get_settings()
logger = logging.getLogger(settings.app_name)

app = FastAPI(
    title="Finance Service",
    version="0.1.0",
    description="Каркас сервиса финансовых операций.",
)


@app.get("/health/live")
async def health_live() -> Dict[str, str]:
    """Эндпоинт для проверки, что процесс живой."""
    return {"status": "live"}


@app.get("/health/ready")
async def health_ready() -> Dict[str, str]:
    """Эндпоинт для проверки готовности приложения."""
    return {"status": "ready"}


@app.on_event("startup")
async def on_startup() -> None:
    """Выводит информацию при старте сервиса."""
    logger.info(
        "Сервис %s запущен на %s:%s с БД %s",
        settings.app_name,
        settings.host,
        settings.port,
        settings.database_url,
    )


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Финализирует работу сервиса."""
    logger.info("Сервис %s завершает работу", settings.app_name)


async def _notify(user_id: str, payload: dict) -> None:
    """Отправляет событие в notification-service, логирует warning при неудаче."""
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(settings.notification_url, json=payload)
    except httpx.HTTPError as exc:
        logger.warning("Не удалось отправить уведомление: %s", exc)


@app.post(
    "/finance/transactions",
    status_code=status.HTTP_201_CREATED,
    response_model=TransactionResponse,
)
async def create_transaction(
    payload: TransactionCreate,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> TransactionResponse:
    """
    Создает операцию дохода/расхода для текущего пользователя.

    После успешного сохранения пытается отправить лог в notification-service.
    """
    tx = Transaction(
        user_id=current_user["user_id"],
        type=payload.type,
        amount=payload.amount,
        category=payload.category,
        description=payload.description,
        occurred_at=payload.occurred_at,
    )
    session.add(tx)
    await session.commit()
    await session.refresh(tx)

    # fire-and-forget уведомление
    message = f"Добавлена операция {payload.type} на сумму {payload.amount}"
    notify_payload = {
        "user_id": current_user["user_id"],
        "event_type": "finance.transaction_created",
        "message": message,
        "payload": {
            "transaction_id": str(tx.id),
            "type": payload.type,
            "amount": str(payload.amount),
            "category": payload.category,
        },
    }
    await _notify(current_user["user_id"], notify_payload)

    return TransactionResponse(
        id=str(tx.id),
        user_id=str(tx.user_id),
        type=tx.type,
        amount=Decimal(tx.amount),
        category=tx.category,
        description=tx.description,
        occurred_at=tx.occurred_at,
        created_at=tx.created_at,
    )


@app.get("/finance/transactions", response_model=TransactionsListResponse)
async def list_transactions(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> TransactionsListResponse:
    """
    Возвращает операции пользователя с пагинацией, отсортированные по occurred_at DESC.
    """
    stmt = (
        select(Transaction)
        .where(Transaction.user_id == current_user["user_id"])
        .order_by(Transaction.occurred_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    items = result.scalars().all()

    count_stmt = select(func.count()).where(Transaction.user_id == current_user["user_id"])
    total = (await session.execute(count_stmt)).scalar_one()

    return TransactionsListResponse(
        items=[
            TransactionResponse(
                id=str(tx.id),
                user_id=str(tx.user_id),
                type=tx.type,
                amount=Decimal(tx.amount),
                category=tx.category,
                description=tx.description,
                occurred_at=tx.occurred_at,
                created_at=tx.created_at,
            )
            for tx in items
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/finance/stats/summary", response_model=SummaryResponse)
async def stats_summary(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SummaryResponse:
    """Возвращает агрегаты: сумма доходов, расходов и баланс."""

    try:
        stmt = (
            select(
                func.coalesce(
                    func.sum(case((Transaction.type == "income", Transaction.amount))), 0
                ).label("income"),
                func.coalesce(
                    func.sum(case((Transaction.type == "expense", Transaction.amount))), 0
                ).label("expense"),
            )
            .where(Transaction.user_id == current_user["user_id"])
        )
        result = await session.execute(stmt)
        income, expense = result.one()
        income = Decimal(income or 0)
        expense = Decimal(expense or 0)
        balance = income - expense
        return SummaryResponse(total_income=income, total_expense=expense, balance=balance)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Ошибка /finance/stats/summary", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось загрузить сводку",
        ) from exc


@app.get("/finance/stats/by-category", response_model=CategoryStatsResponse)
async def stats_by_category(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CategoryStatsResponse:
    """Суммы по категориям отдельно для income и expense."""
    stmt = (
        select(Transaction.type, Transaction.category, func.sum(Transaction.amount))
        .where(Transaction.user_id == current_user["user_id"])
        .group_by(Transaction.type, Transaction.category)
    )
    rows = (await session.execute(stmt)).all()
    income_map: dict[str, Decimal] = {}
    expense_map: dict[str, Decimal] = {}
    for t_type, category, amount in rows:
        if t_type == "income":
            income_map[category] = Decimal(amount)
        else:
            expense_map[category] = Decimal(amount)
    return CategoryStatsResponse(income=income_map, expense=expense_map)


@app.get("/finance/stats/by-day", response_model=DayStatsResponse)
async def stats_by_day(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    days: int = Query(30, ge=1, le=365),
) -> DayStatsResponse:
    """
    Суммы по дням за последние N дней (по occurred_at).

    Использует агрегирование по дате.
    """

    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(
                func.date(Transaction.occurred_at).label("day"),
                func.sum(
                    case((Transaction.type == "income", Transaction.amount), else_=0)
                ).label("income"),
                func.sum(
                    case((Transaction.type == "expense", Transaction.amount), else_=0)
                ).label("expense"),
            )
            .where(
                Transaction.user_id == current_user["user_id"],
                Transaction.occurred_at >= cutoff,
            )
            .group_by(func.date(Transaction.occurred_at))
            .order_by(func.date(Transaction.occurred_at))
        )
        rows = (await session.execute(stmt)).all()
        items = []
        for row in rows:
            items.append(
                DayStatsItem(
                    date=datetime.combine(row.day, datetime.min.time()),
                    income=Decimal(row.income or 0),
                    expense=Decimal(row.expense or 0),
                )
            )
        return DayStatsResponse(items=items)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Ошибка /finance/stats/by-day", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось загрузить статистику по дням",
        ) from exc
