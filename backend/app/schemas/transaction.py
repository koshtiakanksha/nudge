import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amount: float
    date: date
    merchant_name: str | None
    category: str | None
    nudge_category: str | None
    subcategory: str | None = None
    transaction_type: str | None = None
    is_non_negotiable: bool
    is_recurring: bool = False
    is_anomaly: bool = False
    is_ignored: bool = False
    confidence_score: float | None = None
    raw_description: str | None = None


class TransactionUpdate(BaseModel):
    nudge_category: str | None = None
    is_non_negotiable: bool | None = None
    merchant_name: str | None = None
    subcategory: str | None = None
    transaction_type: str | None = None
    is_recurring: bool | None = None
    is_anomaly: bool | None = None
    is_ignored: bool | None = None


class TransactionListResponse(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    page_size: int
