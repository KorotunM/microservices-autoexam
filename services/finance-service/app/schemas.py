"""Схемы запросов/ответов для сервиса финансов."""
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, condecimal


class TransactionCreate(BaseModel):
    """Запрос на создание операции."""

    type: Literal["income", "expense"]
    amount: condecimal(max_digits=12, decimal_places=2, gt=0)  # type: ignore
    category: str = Field(..., max_length=64)
    description: Optional[str] = None
    occurred_at: datetime = Field(default_factory=datetime.utcnow)


class TransactionResponse(BaseModel):
    """Ответ с созданной операцией."""

    id: str
    user_id: str
    type: Literal["income", "expense"]
    amount: Decimal
    category: str
    description: Optional[str] = None
    occurred_at: datetime
    created_at: datetime


class TransactionsListResponse(BaseModel):
    """Список операций с пагинацией."""

    items: list[TransactionResponse]
    total: int
    limit: int
    offset: int


class SummaryResponse(BaseModel):
    """Агрегаты доходов/расходов."""

    total_income: Decimal
    total_expense: Decimal
    balance: Decimal


class CategoryStatsResponse(BaseModel):
    """Суммы по категориям."""

    income: dict[str, Decimal]
    expense: dict[str, Decimal]


class DayStatsItem(BaseModel):
    """Сумма по дню."""

    date: datetime
    income: Decimal
    expense: Decimal


class DayStatsResponse(BaseModel):
    """Суммы по дням."""

    items: list[DayStatsItem]
