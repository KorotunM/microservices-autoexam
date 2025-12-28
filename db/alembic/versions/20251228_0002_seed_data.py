"""Seed пользователей и транзакций."""
from datetime import datetime, timedelta
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import select
from passlib.context import CryptContext

# revision identifiers, used by Alembic.
revision = "20251228_0002_seed_data"
down_revision = "20251228_0001"
branch_labels = None
depends_on = None

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _ensure_user(conn, username: str, password: str) -> str:
    """Создает пользователя, если его нет. Возвращает id."""
    users = sa.table(
        "users",
        sa.column("id", sa.dialects.postgresql.UUID(as_uuid=False)),
        sa.column("username", sa.String),
        sa.column("password_hash", sa.Text),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    existing = conn.execute(select(users.c.id).where(users.c.username == username)).scalar()
    if existing:
        return existing
    user_id = str(uuid.uuid4())
    conn.execute(
        users.insert().values(
            id=user_id,
            username=username,
            password_hash=pwd_context.hash(password),
            created_at=datetime.utcnow(),
        )
    )
    return user_id


def _seed_transactions(conn, user_id: str) -> None:
    """Создает базовые транзакции для пользователя, если их еще нет."""
    tx = sa.table(
        "transactions",
        sa.column("id", sa.dialects.postgresql.UUID(as_uuid=False)),
        sa.column("user_id", sa.dialects.postgresql.UUID(as_uuid=False)),
        sa.column("type", sa.String),
        sa.column("amount", sa.Numeric(12, 2)),
        sa.column("category", sa.String),
        sa.column("description", sa.Text),
        sa.column("occurred_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    existing = conn.execute(
        select(tx.c.id).where(tx.c.user_id == user_id, tx.c.description.like("seed:%"))
    ).fetchone()
    if existing:
        return

    now = datetime.utcnow()
    data = [
        ("income", 1000, "salary", "seed:income1", now - timedelta(days=2)),
        ("income", 500, "bonus", "seed:income2", now - timedelta(days=4)),
        ("expense", 200, "food", "seed:expense1", now - timedelta(days=1)),
        ("expense", 150, "transport", "seed:expense2", now - timedelta(days=3)),
    ]
    for t_type, amount, category, desc, at in data:
        conn.execute(
            tx.insert().values(
                id=str(uuid.uuid4()),
                user_id=user_id,
                type=t_type,
                amount=amount,
                category=category,
                description=desc,
                occurred_at=at,
                created_at=now,
            )
        )


def upgrade() -> None:
    conn = op.get_bind()
    admin_id = _ensure_user(conn, "admin", "admin")
    _ensure_user(conn, "Sanchez", "Sanek228")
    _seed_transactions(conn, admin_id)


def downgrade() -> None:
    conn = op.get_bind()
    tx = sa.table(
        "transactions",
        sa.column("user_id", sa.dialects.postgresql.UUID(as_uuid=False)),
        sa.column("description", sa.Text),
    )
    users = sa.table(
        "users",
        sa.column("username", sa.String),
    )
    conn.execute(tx.delete().where(tx.c.description.like("seed:%")))
    conn.execute(users.delete().where(users.c.username.in_(["admin", "Sanchez"])))

