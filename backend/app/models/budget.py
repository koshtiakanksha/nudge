import uuid
from datetime import date as date_type
from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)

    month: Mapped[date_type] = mapped_column(Date)  # first of month

    # { "dining": {"allocated": 300, "spent": 120, "is_non_neg": false}, ... }
    allocations: Mapped[dict] = mapped_column(JSONB, default=dict)

    buffer_reserved: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_allocated: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    income_estimate: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    total_budget: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    generated_by_ai: Mapped[bool] = mapped_column(Boolean, default=True)
    generated_from_statement: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    engine_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
