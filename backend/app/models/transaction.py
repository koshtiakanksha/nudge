import uuid
from datetime import date as date_type
from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Transaction(Base):
    """
    Transaction ledger. Converted to a TimescaleDB hypertable on `date`
    via migration 0002 (see migrations/) for efficient time-range queries
    at scale. SQLAlchemy treats it as a normal table; Timescale's chunking
    is transparent at the ORM layer.
    """
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)

    plaid_transaction_id: Mapped[str] = mapped_column(String, unique=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    date: Mapped[date_type] = mapped_column(Date, index=True)

    merchant_name: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str | None] = mapped_column(String, nullable=True)  # raw Plaid category
    nudge_category: Mapped[str | None] = mapped_column(String, nullable=True)  # Claude-assigned lifestyle bucket
    subcategory: Mapped[str | None] = mapped_column(String, nullable=True)
    transaction_type: Mapped[str | None] = mapped_column(String, nullable=True)
    is_non_negotiable: Mapped[bool] = mapped_column(Boolean, default=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False)
    is_ignored: Mapped[bool] = mapped_column(Boolean, default=False)

    account_id: Mapped[str | None] = mapped_column(String, nullable=True)
    statement_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("statement_uploads.id"), nullable=True, index=True)
    raw_description: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    location_city: Mapped[str | None] = mapped_column(String, nullable=True)
    location_state: Mapped[str | None] = mapped_column(String, nullable=True)
    location_country: Mapped[str | None] = mapped_column(String, nullable=True)
    currency: Mapped[str] = mapped_column(String, default="USD")
    raw_data: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
