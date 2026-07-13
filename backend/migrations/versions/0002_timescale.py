"""enable timescaledb and convert transactions to hypertable

Revision ID: 0002_timescale
Revises: 0001_initial
Create Date: 2026-06-18

NOTE: This migration requires the TimescaleDB extension to be available on
the Postgres instance (Supabase: enable via Database > Extensions >
"timescaledb", or self-hosted: use the timescale/timescaledb-ha image).
If TimescaleDB isn't available in your environment, skip this migration
(stamp past it) -- the app works fine on plain Postgres, just without
hypertable chunking benefits at very large scale.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002_timescale"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
    # Timescale requires the partitioning column to be part of any unique
    # constraint, so we drop the plain unique index on plaid_transaction_id
    # and re-add it as a composite unique constraint including `date`.
    op.execute("ALTER TABLE transactions DROP CONSTRAINT IF EXISTS transactions_plaid_transaction_id_key;")
    op.execute(
        "ALTER TABLE transactions ADD CONSTRAINT uq_transactions_plaid_id_date "
        "UNIQUE (plaid_transaction_id, date);"
    )

    # The primary key on `id` alone hits the same rule and was missed
    # originally -- create_hypertable() fails on it with "cannot create a
    # unique index without the column date (used in partitioning)".
    # anomalies.transaction_id has a single-column FK into transactions.id;
    # a composite (id, date) primary key can no longer back that FK
    # (Postgres requires the referenced columns to exactly match a unique
    # constraint), so we drop it and rely on app-level integrity for that
    # one relationship, same tradeoff Timescale docs recommend for
    # hypertables referenced by other tables. Add an explicit index so we
    # don't lose lookup performance on anomalies.transaction_id.
    op.execute("ALTER TABLE anomalies DROP CONSTRAINT IF EXISTS anomalies_transaction_id_fkey;")
    op.execute("ALTER TABLE transactions DROP CONSTRAINT IF EXISTS transactions_pkey;")
    op.execute("ALTER TABLE transactions ADD CONSTRAINT transactions_pkey PRIMARY KEY (id, date);")
    op.create_index("ix_anomalies_transaction_id", "anomalies", ["transaction_id"], if_not_exists=True)

    op.execute(
        "SELECT create_hypertable('transactions', 'date', "
        "chunk_time_interval => INTERVAL '1 month', if_not_exists => TRUE, migrate_data => TRUE);"
    )


def downgrade() -> None:
    # Hypertables can't be cleanly "un-converted"; downgrading drops and
    # recreates the table as plain Postgres (data loss). Acceptable for a
    # dev-only downgrade path.
    op.drop_index("ix_anomalies_transaction_id", table_name="anomalies", if_exists=True)
    op.execute("ALTER TABLE transactions DROP CONSTRAINT IF EXISTS transactions_pkey;")
    op.execute("ALTER TABLE transactions ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);")
    op.execute(
        "ALTER TABLE anomalies ADD CONSTRAINT anomalies_transaction_id_fkey "
        "FOREIGN KEY (transaction_id) REFERENCES transactions(id);"
    )
    op.execute("ALTER TABLE transactions DROP CONSTRAINT IF EXISTS uq_transactions_plaid_id_date;")
    op.execute(
        "ALTER TABLE transactions ADD CONSTRAINT transactions_plaid_transaction_id_key "
        "UNIQUE (plaid_transaction_id);"
    )