import uuid
from datetime import date as date_type
from datetime import datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AffordabilityCheck(Base):
    __tablename__ = "affordability_checks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    item_name: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    category: Mapped[str] = mapped_column(String, default="Other")
    need_or_want: Mapped[str] = mapped_column(String, default="want")
    purchase_date: Mapped[date_type] = mapped_column(Date, nullable=False)
    product_url: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    verdict: Mapped[str] = mapped_column(String, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    safe_to_spend_before: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    safe_to_spend_after: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    remaining_before: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    remaining_after: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    category_impact: Mapped[dict] = mapped_column(JSONB, default=dict)
    forecast_impact: Mapped[dict] = mapped_column(JSONB, default=dict)
    upcoming_bill_risk: Mapped[str] = mapped_column(String, default="low")
    suggested_actions: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
