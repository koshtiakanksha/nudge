import uuid
from datetime import date as date_type
from datetime import datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class BudgetRecommendation(Base):
    __tablename__ = "budget_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    month: Mapped[date_type] = mapped_column(Date, index=True)
    category: Mapped[str] = mapped_column(String, nullable=False)
    recommended_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    reasoning: Mapped[str] = mapped_column(Text, default="")
    confidence_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0.6)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
