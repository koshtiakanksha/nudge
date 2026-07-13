import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PlaidItem(Base):
    """One row per linked bank institution (a Plaid 'Item')."""
    __tablename__ = "plaid_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)

    item_id: Mapped[str] = mapped_column(String, unique=True)
    # Encrypted with Fernet (see app/core/security.py) before being persisted.
    access_token_encrypted: Mapped[str] = mapped_column(String)

    institution_name: Mapped[str] = mapped_column(String)
    # [{ "account_id": "...", "name": "...", "type": "depository", "mask": "1234", "balance": 1234.56 }]
    accounts: Mapped[list] = mapped_column(JSONB, default=list)

    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
