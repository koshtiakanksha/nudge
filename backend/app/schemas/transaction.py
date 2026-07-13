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
    is_non_negotiable: bool


class TransactionUpdate(BaseModel):
    nudge_category: str | None = None
    is_non_negotiable: bool | None = None


class TransactionListResponse(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    page_size: int
