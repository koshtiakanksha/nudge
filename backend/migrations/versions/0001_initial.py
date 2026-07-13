"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("monthly_income", sa.Numeric(12, 2), nullable=True),
        sa.Column("spend_ceiling", sa.Numeric(12, 2), nullable=True),
        sa.Column("buffer_pct", sa.Numeric(5, 4), nullable=False, server_default="0.10"),
        sa.Column("location_lat", sa.Numeric(9, 6), nullable=True),
        sa.Column("location_lng", sa.Numeric(9, 6), nullable=True),
        sa.Column("cards", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("onboarding_complete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "plaid_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("item_id", sa.String(), nullable=False, unique=True),
        sa.Column("access_token_encrypted", sa.String(), nullable=False),
        sa.Column("institution_name", sa.String(), nullable=False),
        sa.Column("accounts", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_plaid_items_user_id", "plaid_items", ["user_id"])

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("plaid_transaction_id", sa.String(), nullable=False, unique=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("merchant_name", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("nudge_category", sa.String(), nullable=True),
        sa.Column("is_non_negotiable", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("account_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])
    op.create_index("ix_transactions_date", "transactions", ["date"])

    op.create_table(
        "budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("allocations", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("buffer_reserved", sa.Numeric(12, 2), server_default="0"),
        sa.Column("total_allocated", sa.Numeric(12, 2), server_default="0"),
        sa.Column("generated_by_ai", sa.Boolean(), server_default="true"),
        sa.Column("ai_reasoning", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_budgets_user_id", "budgets", ["user_id"])

    op.create_table(
        "price_watches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("product_url", sa.String(), nullable=False),
        sa.Column("product_name", sa.String(), nullable=True),
        sa.Column("retailer", sa.String(), nullable=True),
        sa.Column("current_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("target_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("price_history", postgresql.JSONB(), server_default="[]"),
        sa.Column("verdict", sa.String(), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 2), nullable=True),
        sa.Column("alert_sent", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_price_watches_user_id", "price_watches", ["user_id"])

    op.create_table(
        "anomalies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id"), nullable=False),
        sa.Column("anomaly_score", sa.Numeric(6, 4), nullable=False),
        sa.Column("merchant_name", sa.String(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("ai_context", sa.Text(), nullable=True),
        sa.Column("user_marked_intentional", sa.Boolean(), nullable=True),
        sa.Column("notified", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_anomalies_user_id", "anomalies", ["user_id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chart_data", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"])
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"])


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("anomalies")
    op.drop_table("price_watches")
    op.drop_table("budgets")
    op.drop_table("transactions")
    op.drop_table("plaid_items")
    op.drop_table("users")
