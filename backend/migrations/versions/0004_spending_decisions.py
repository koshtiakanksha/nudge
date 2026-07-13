"""spending decisions

Revision ID: 0004_spending_decisions
Revises: 0003_statement_analyzer
Create Date: 2026-06-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_spending_decisions"
down_revision: Union[str, None] = "0003_statement_analyzer"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "affordability_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("item_name", sa.String(), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("category", sa.String(), nullable=False, server_default="Other"),
        sa.Column("need_or_want", sa.String(), nullable=False, server_default="want"),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("product_url", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("verdict", sa.String(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("safe_to_spend_before", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("safe_to_spend_after", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("remaining_before", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("remaining_after", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("category_impact", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("forecast_impact", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("upcoming_bill_risk", sa.String(), nullable=False, server_default="low"),
        sa.Column("suggested_actions", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_affordability_checks_user_id", "affordability_checks", ["user_id"])
    op.add_column("budget_categories", sa.Column("category_type", sa.String(), nullable=False, server_default="flexible"))
    op.add_column("budget_categories", sa.Column("is_disabled", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("budget_categories", "is_disabled")
    op.drop_column("budget_categories", "category_type")
    op.drop_table("affordability_checks")
