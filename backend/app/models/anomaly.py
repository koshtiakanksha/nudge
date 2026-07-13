import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Anomaly(Base):
    """Statistical outliers flagged by Isolation Forest, enriched with Claude context."""
    __tablename__ = "anomalies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    transaction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("transactions.id"))

    anomaly_score: Mapped[float] = mapped_column(Numeric(6, 4))  # Isolation Forest score
    merchant_name: Mapped[str | None] = mapped_column(String, nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))

    ai_context: Mapped[str | None] = mapped_column(Text, nullable=True)  # Claude's human-readable explanation
    user_marked_intentional: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
