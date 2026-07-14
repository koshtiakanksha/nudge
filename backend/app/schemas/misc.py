import uuid
from datetime import date

from pydantic import BaseModel


# --- Forecast ---
class ForecastPoint(BaseModel):
    date: date
    predicted_spend: float
    lower_bound: float
    upper_bound: float


class ForecastResponse(BaseModel):
    points: list[ForecastPoint]
    month_end_projection: float
    ceiling: float | None
    on_track: bool
    days_remaining: int
    model_used: str = "unknown"  # "prophet" | "fallback_moving_average" | "none"


# --- Dashboard ---
class DashboardSummary(BaseModel):
    month_to_date_spend: float
    month_to_date_income: float
    buffer_status: float  # 0-1, pct of buffer remaining
    top_categories: list[dict]
    spend_ceiling: float | None
    projected_month_end: float
    recent_anomalies: int
    active_price_watches: int


# --- Anomalies ---
class AnomalyOut(BaseModel):
    id: uuid.UUID
    transaction_id: uuid.UUID
    merchant_name: str | None
    amount: float
    anomaly_score: float
    ai_context: str | None
    user_marked_intentional: bool | None
    created_at: str


class AnomalyFeedback(BaseModel):
    intentional: bool


# --- Price Watch ---
class PriceWatchCreate(BaseModel):
    product_url: str
    target_price: float | None = None


class PriceWatchOut(BaseModel):
    id: uuid.UUID
    product_url: str
    product_name: str | None
    retailer: str | None
    image_url: str | None = None
    current_price: float | None
    target_price: float | None
    price_history: list[dict]
    verdict: str | None
    verdict_reason: str | None = None
    confidence: float | None
    deal_score: float | None = None
    affordability_score: float | None = None
    buy_wait_recommendation: str | None = None


# --- Deals ---
class DealOut(BaseModel):
    title: str
    description: str
    category: str
    result_type: str = "deal"
    location: str | None = None
    address: str | None = None
    distance_miles: float | None = None
    source: str
    provider: str | None = None
    image_url: str | None = None
    price: float | None = None
    cost: str | None = None
    rating: float | None = None
    url: str | None = None
    external_url: str | None = None
    website_url: str | None = None
    ticket_url: str | None = None
    directions_url: str | None = None
    expires_at: str | None = None
    starts_at: str | None = None
    ends_at: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    last_updated: str | None = None
    is_sample: bool = False
    affordability_label: str | None = None


# --- Chat ---
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    chart_data: dict | None = None
    actions: list[dict] = []


class ChatHistoryItem(BaseModel):
    role: str
    content: str
    chart_data: dict | None = None
    created_at: str
