import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict


class BudgetAllocation(BaseModel):
    allocated: float
    spent: float = 0
    is_non_neg: bool = False


class BudgetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    month: date
    allocations: dict[str, BudgetAllocation]
    buffer_reserved: float
    total_allocated: float
    generated_by_ai: bool
    ai_reasoning: str | None


class BudgetGenerateRequest(BaseModel):
    month: date | None = None  # defaults to current month
    regenerate: bool = False


class BudgetAdjustRequest(BaseModel):
    category: str
    new_allocated: float
