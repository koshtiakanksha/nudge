from pydantic import BaseModel


class ScenarioRequest(BaseModel):
    # "category_change" | "income_change" | "one_time_expense"
    scenario_type: str
    # category_change
    category: str | None = None
    new_amount: float | None = None
    # income_change
    new_income_estimate: float | None = None
    # one_time_expense
    amount: float | None = None


class ScenarioChangeOut(BaseModel):
    category: str
    previous_amount: float
    current_amount: float
    delta: float


class ScenarioResponse(BaseModel):
    scenario: str
    income_before: float
    income_after: float
    spendable_before: float
    spendable_after: float
    before_allocations: dict[str, dict]
    after_allocations: dict[str, dict]
    changes: list[ScenarioChangeOut]
    risk_level: str
    summary: str
