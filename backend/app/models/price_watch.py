import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PriceWatch(Base):
    __tablename__ = "price_watches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)

    product_url: Mapped[str] = mapped_column(String)
    product_name: Mapped[str | None] = mapped_column(String, nullable=True)
    retailer: Mapped[str | None] = mapped_column(String, nullable=True)

    current_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    target_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    # [{ "date": "2026-01-01", "price": 199.99 }, ...]
    price_history: Mapped[list] = mapped_column(JSONB, default=list)

    verdict: Mapped[str | None] = mapped_column(String, nullable=True)  # buy_now | wait | overpriced
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    alert_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
