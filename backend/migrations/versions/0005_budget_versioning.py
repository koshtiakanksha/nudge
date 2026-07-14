"""add engine/prompt version tracking to budgets

Revision ID: 0005_budget_versioning
Revises: 0004_spending_decisions
Create Date: 2026-07-13

Part of the Phase 1 deterministic-budget-engine rework: budgets.allocations
is now always computed by app.services.budget_engine (a pure function),
not the LLM. These columns record which engine and prompt version
produced a given budget row, so future monitoring (Phase 4) can track
behavior across versions as the engine evolves.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_budget_versioning"
down_revision: Union[str, None] = "0004_spending_decisions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("budgets", sa.Column("engine_version", sa.Text(), nullable=True))
    op.add_column("budgets", sa.Column("prompt_version", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("budgets", "prompt_version")
    op.drop_column("budgets", "engine_version")
