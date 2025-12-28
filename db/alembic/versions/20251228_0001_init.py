"""Инициализация схемы (users, profiles, transactions, notification_logs)."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20251228_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создает основные таблицы и индексы."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("username", sa.String(length=64), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("full_name", sa.String(length=128), nullable=True),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("email", name="profiles_email_unique"),
    )

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("category", sa.String(length=64), server_default=sa.text("'general'::varchar"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("type IN ('income','expense')", name="transactions_type_check"),
        sa.CheckConstraint("amount > 0", name="transactions_amount_check"),
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_transactions_user_occurred ON transactions (user_id, occurred_at DESC);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_transactions_user_type ON transactions (user_id, type);"
    )

    op.create_table(
        "notification_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=64), server_default=sa.text("'event'::varchar"), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_notification_logs_user_time ON notification_logs (user_id, created_at DESC);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_notification_logs_event_time ON notification_logs (event_type, created_at DESC);"
    )


def downgrade() -> None:
    """Откатывает изменения."""
    op.drop_index("idx_notification_logs_event_time", table_name="notification_logs")
    op.drop_index("idx_notification_logs_user_time", table_name="notification_logs")
    op.drop_table("notification_logs")

    op.drop_index("idx_transactions_user_type", table_name="transactions")
    op.drop_index("idx_transactions_user_occurred", table_name="transactions")
    op.drop_table("transactions")

    op.drop_table("profiles")
    op.drop_table("users")
