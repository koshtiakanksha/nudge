"""statement analyzer

Revision ID: 0003_statement_analyzer
Revises: 0002_timescale
Create Date: 2026-06-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_statement_analyzer"
down_revision: Union[str, None] = "0002_timescale"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "statement_uploads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("file_type", sa.String(), nullable=False),
        sa.Column("statement_month", sa.Date(), nullable=False),
        sa.Column("bank_name", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="uploaded"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("upload_date", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_statement_uploads_user_id", "statement_uploads", ["user_id"])

    op.add_column("transactions", sa.Column("statement_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("transactions", sa.Column("subcategory", sa.String(), nullable=True))
    op.add_column("transactions", sa.Column("transaction_type", sa.String(), nullable=True))
    op.add_column("transactions", sa.Column("is_recurring", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("transactions", sa.Column("is_anomaly", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("transactions", sa.Column("is_ignored", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("transactions", sa.Column("raw_description", sa.String(), nullable=True))
    op.add_column("transactions", sa.Column("confidence_score", sa.Numeric(5, 2), nullable=True))
    op.add_column("transactions", sa.Column("location_city", sa.String(), nullable=True))
    op.add_column("transactions", sa.Column("location_state", sa.String(), nullable=True))
    op.add_column("transactions", sa.Column("location_country", sa.String(), nullable=True))
    op.add_column("transactions", sa.Column("currency", sa.String(), nullable=False, server_default="USD"))
    op.add_column("transactions", sa.Column("raw_data", postgresql.JSONB(), nullable=False, server_default="{}"))
    op.create_index("ix_transactions_statement_id", "transactions", ["statement_id"])
    op.create_foreign_key("fk_transactions_statement_id", "transactions", "statement_uploads", ["statement_id"], ["id"])

    op.add_column("anomalies", sa.Column("anomaly_type", sa.String(), nullable=False, server_default="unusual_amount"))
    op.add_column("anomalies", sa.Column("explanation", sa.Text(), nullable=True))
    op.add_column("anomalies", sa.Column("severity", sa.String(), nullable=False, server_default="low"))
    op.add_column("anomalies", sa.Column("user_status", sa.String(), nullable=False, server_default="pending"))

    op.add_column("budgets", sa.Column("income_estimate", sa.Numeric(12, 2), nullable=True))
    op.add_column("budgets", sa.Column("total_budget", sa.Numeric(12, 2), nullable=True))
    op.add_column("budgets", sa.Column("generated_from_statement", sa.Boolean(), nullable=False, server_default="false"))

    op.create_table(
        "category_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("merchant_key", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_category_rules_user_id", "category_rules", ["user_id"])
    op.create_index("ix_category_rules_merchant_key", "category_rules", ["merchant_key"])

    op.create_table(
        "budget_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("monthly_limit", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_budget_categories_user_id", "budget_categories", ["user_id"])

    op.create_table(
        "budget_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("recommended_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("reasoning", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence_score", sa.Numeric(5, 2), nullable=False, server_default="0.6"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_budget_recommendations_user_id", "budget_recommendations", ["user_id"])
    op.create_index("ix_budget_recommendations_month", "budget_recommendations", ["month"])

    op.create_table(
        "recurring_expenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("merchant_name", sa.String(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("frequency", sa.String(), nullable=False, server_default="monthly"),
        sa.Column("next_expected_date", sa.Date(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 2), nullable=False, server_default="0.6"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_recurring_expenses_user_id", "recurring_expenses", ["user_id"])


def downgrade() -> None:
    op.drop_table("recurring_expenses")
    op.drop_table("budget_recommendations")
    op.drop_table("budget_categories")
    op.drop_table("category_rules")
    op.drop_column("budgets", "generated_from_statement")
    op.drop_column("budgets", "total_budget")
    op.drop_column("budgets", "income_estimate")
    op.drop_column("anomalies", "user_status")
    op.drop_column("anomalies", "severity")
    op.drop_column("anomalies", "explanation")
    op.drop_column("anomalies", "anomaly_type")
    op.drop_constraint("fk_transactions_statement_id", "transactions", type_="foreignkey")
    op.drop_index("ix_transactions_statement_id", table_name="transactions")
    for column in [
        "raw_data", "currency", "location_country", "location_state", "location_city",
        "confidence_score", "raw_description", "is_ignored", "is_anomaly", "is_recurring",
        "transaction_type", "subcategory", "statement_id",
    ]:
        op.drop_column("transactions", column)
    op.drop_table("statement_uploads")
