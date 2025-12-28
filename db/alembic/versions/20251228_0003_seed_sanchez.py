"""Добавление пользователя Sanchez (идемпотентно)."""
from datetime import datetime
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import select
from passlib.context import CryptContext

# revision identifiers, used by Alembic.
revision = "20251228_0003_seed_sanchez"
down_revision = "20251228_0002_seed_data"
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


def upgrade() -> None:
    conn = op.get_bind()
    _ensure_user(conn, "Sanchez", "Sanek228")


def downgrade() -> None:
    conn = op.get_bind()
    users = sa.table("users", sa.column("username", sa.String))
    conn.execute(users.delete().where(users.c.username == "Sanchez"))
