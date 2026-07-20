"""add constrained_tiers and validation_warnings to budgets

Revision ID: 0006_budget_evidence
Revises: 0005_budget_versioning
Create Date: 2026-07-20

Part of wiring compute_budget_allocation_v2's role-priority waterfall
(fixed_essential > variable_essential > savings_or_debt > discretionary)
into budgets.py's manual-income flow -- the app/smart-budget page
already surfaces this kind of evidence (see the income_stability /
category_evidence fields added to statements.budget_recommendations),
but the manual /budgets/generate flow had nowhere to store it.
Generation-time snapshots, same pattern as engine_version/prompt_version
from 0005 -- not recomputed on fetch.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_budget_evidence"
down_revision: Union[str, None] = "0005_budget_versioning"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("budgets", sa.Column("constrained_tiers", postgresql.JSONB(), nullable=True))
    op.add_column("budgets", sa.Column("validation_warnings", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("budgets", "validation_warnings")
    op.drop_column("budgets", "constrained_tiers")
