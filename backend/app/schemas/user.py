import uuid

from pydantic import BaseModel, ConfigDict


class CardInput(BaseModel):
    name: str
    cashback_rules: dict[str, float] = {}


class UserProfileUpdate(BaseModel):
    monthly_income: float | None = None
    spend_ceiling: float | None = None
    buffer_pct: float | None = None
    location_lat: float | None = None
    location_lng: float | None = None
    cards: list[CardInput] | None = None


class UserProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    monthly_income: float | None
    spend_ceiling: float | None
    buffer_pct: float
    location_lat: float | None
    location_lng: float | None
    cards: list[dict]
    onboarding_complete: bool
