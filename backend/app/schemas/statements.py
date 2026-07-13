import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class StatementUploadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_name: str
    file_type: str
    statement_month: date
    bank_name: str | None
    upload_date: datetime
    status: str
    error_message: str | None


class StatementUploadResponse(BaseModel):
    statement: StatementUploadOut
    parsed_count: int
    needs_mapping: bool = False
    message: str


class StatementTransactionOut(BaseModel):
    id: uuid.UUID
    transaction_id: str
    date: date
    description: str
    merchant_name: str | None
    amount: float
    transaction_type: str
    category: str | None
    subcategory: str | None = None
    bank_name: str | None = None
    source_statement_id: uuid.UUID | None = None
    raw_description: str | None = None
    confidence_score: float | None = None
    location_city: str | None = None
    location_state: str | None = None
    location_country: str | None = None
    currency: str = "USD"
    is_recurring: bool = False
    is_anomaly: bool = False
    is_ignored: bool = False


class TransactionReviewUpdate(BaseModel):
    merchant_name: str | None = None
    nudge_category: str | None = None
    subcategory: str | None = None
    transaction_type: str | None = None
    is_recurring: bool | None = None
    is_anomaly: bool | None = None
    is_ignored: bool | None = None
    apply_to_similar: bool = False


class BulkTransactionUpdate(BaseModel):
    transaction_ids: list[uuid.UUID]
    nudge_category: str | None = None
    is_ignored: bool | None = None
    is_recurring: bool | None = None
    apply_to_similar: bool = False


class SpendingSummaryOut(BaseModel):
    total_income: float
    total_spending: float
    net_cash_flow: float
    average_daily_spending: float
    average_weekly_spending: float
    savings_rate: float | None
    transaction_count: int
    months_of_history: int
    prediction_message: str | None = None
    expected_next_month_spending: float | None = None
    expected_next_month_income: float | None = None
    cash_left_after_predicted_expenses: float | None = None


class CategorySpendOut(BaseModel):
    category: str
    amount: float
    transaction_count: int


class MerchantSpendOut(BaseModel):
    merchant_name: str
    amount: float
    transaction_count: int


class TrendPointOut(BaseModel):
    month: str
    income: float
    spending: float


class InsightOut(BaseModel):
    title: str
    detail: str
    severity: str = "info"


class RecurringExpenseOut(BaseModel):
    id: uuid.UUID | None = None
    merchant_name: str
    amount: float
    frequency: str
    next_expected_date: date | None
    category: str | None
    confidence_score: float


class StatementAnomalyOut(BaseModel):
    id: uuid.UUID | None = None
    transaction_id: uuid.UUID | None = None
    anomaly_type: str
    explanation: str
    severity: str
    user_status: str = "pending"
    merchant_name: str | None = None
    amount: float | None = None


class BudgetRecommendationOut(BaseModel):
    category: str
    recommended_amount: float
    reasoning: str
    confidence_score: float


class SmartBudgetOut(BaseModel):
    month: date
    income_estimate: float
    total_budget: float
    recommendations: list[BudgetRecommendationOut]
    warnings: list[str]
    explanation: str


class SaveGeneratedBudgetRequest(BaseModel):
    month: date
    income_estimate: float | None = None
    total_budget: float | None = None
    recommendations: list[BudgetRecommendationOut]


class AnomalyStatusUpdate(BaseModel):
    user_status: str
