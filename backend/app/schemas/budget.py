import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict


class BudgetAllocation(BaseModel):
    allocated: float
    spent: float = 0
    is_non_neg: bool = False


class BudgetCategoryInput(BaseModel):
    name: str
    allocated: float = 0
    spent: float = 0
    is_non_neg: bool = False


class BudgetChange(BaseModel):
    category: str
    previous_amount: float
    current_amount: float
    delta: float


class BudgetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    month: date
    monthly_income: float | None = None
    income_source: str = "unavailable"
    total_budget: float | None = None
    allocations: dict[str, BudgetAllocation]
    buffer_reserved: float
    total_allocated: float
    generated_by_ai: bool
    ai_reasoning: str | None
    engine_version: str | None = None
    prompt_version: str | None = None
    constrained_tiers: list[str] = []
    validation_warnings: list[str] = []
    changes_from_previous: list[BudgetChange] = []


class BudgetGenerateRequest(BaseModel):
    month: date | None = None  # defaults to current month
    regenerate: bool = False


class BudgetAdjustRequest(BaseModel):
    category: str
    new_allocated: float


class BudgetSaveRequest(BaseModel):
    month: date | None = None
    monthly_income: float | None = None
    total_budget: float | None = None
    categories: list[BudgetCategoryInput]
    ai_reasoning: str | None = None
