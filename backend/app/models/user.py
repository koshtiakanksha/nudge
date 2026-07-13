import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class User(Base):
    """
    Mirrors Supabase auth.users via the same UUID primary key.
    Supabase handles email/password auth; this table stores Nudge-specific
    profile and budgeting preference data, keyed 1:1 to the auth user id.
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)

    monthly_income: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    spend_ceiling: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    buffer_pct: Mapped[float] = mapped_column(Numeric(5, 4), default=0.10)

    location_lat: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    location_lng: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)

    # [{ "name": "Chase Sapphire", "cashback_rules": {"dining": 3, "travel": 2} }, ...]
    cards: Mapped[list] = mapped_column(JSONB, default=list)

    onboarding_complete: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
