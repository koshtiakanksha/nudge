import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class TodayOut(BaseModel):
    safe_to_spend_today: float
    safe_to_spend_message: str
    can_calculate: bool
    has_linked_data: bool
    month_to_date_spending: float
    month_end_forecast: float
    spending_ceiling: float | None
    upcoming_bills_total: float
    budget_health: str
    top_risk_category: str | None
    recommended_action: str
    remaining_safe_money: float
    # Was computed by build_decision_context's resolve_monthly_income
    # fallback (added when safe-to-spend stopped requiring manual
    # income) but never passed through here -- meaning a user seeing a
    # safe-to-spend number had no way to tell whether it was based on
    # what they typed in or an estimate from transaction history.
    income_source: str = "unavailable"


class AffordabilityCheckRequest(BaseModel):
    item_name: str
    price: float
    category: str = "Other"
    need_or_want: str = "want"
    purchase_date: date
    product_url: str | None = None
    notes: str | None = None


class AffordabilityCheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID | None = None
    item_name: str
    price: float
    category: str
    need_or_want: str
    purchase_date: date
    product_url: str | None = None
    notes: str | None = None
    verdict: str
    explanation: str
    safe_to_spend_before: float
    safe_to_spend_after: float
    remaining_before: float
    remaining_after: float
    category_impact: dict
    forecast_impact: dict
    upcoming_bill_risk: str
    suggested_actions: list[str]
    created_at: datetime | None = None


class BudgetCategoryOut(BaseModel):
    id: uuid.UUID
    name: str
    monthly_limit: float
    category_type: str
    is_disabled: bool
    is_default: bool


class BudgetCategoryRequest(BaseModel):
    name: str
    monthly_limit: float = 0
    category_type: str = "flexible"
    is_disabled: bool = False
    is_default: bool = False


class RebalanceRequest(BaseModel):
    to_category: str
    amount: float
    from_category: str | None = None
    action: str = "move_money"


class RebalanceOut(BaseModel):
    message: str
    safe_to_spend_change: float
    updated_categories: list[BudgetCategoryOut]


class AppModeOut(BaseModel):
    mode: str
    badges: list[str]
    message: str | None = None
