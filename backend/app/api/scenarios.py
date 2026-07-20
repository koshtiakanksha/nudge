from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.budgets import _category_baselines, _category_roles_for
from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.scenarios import ScenarioRequest, ScenarioResponse
from app.services.income_service import detect_income
from app.services.scenario_simulation_service import (
    simulate_category_change,
    simulate_income_change,
    simulate_one_time_expense,
)

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


async def _income_estimate_for(db: AsyncSession, user_id, user: User | None) -> float:
    """Manual user.monthly_income always wins when set (same precedent
    as decision_context.py's resolve_monthly_income) -- otherwise falls
    back to income_service's conservative estimate from transaction
    history."""
    if user and user.monthly_income is not None:
        return float(user.monthly_income)
    txns = (await db.execute(select(Transaction).where(Transaction.user_id == user_id))).scalars().all()
    return detect_income(txns).conservative_monthly_income


@router.post("/simulate", response_model=ScenarioResponse)
async def simulate_scenario(
    payload: ScenarioRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.id == current.id))).scalar_one_or_none()

    # Same category-baseline and role sources budgets.py already uses --
    # one shared source of truth for "what does this category normally
    # cost" and "what role is it," not a scenario-specific copy.
    spending_by_category = await _category_baselines(db, current.id)
    category_roles = await _category_roles_for(db, current.id, spending_by_category)
    income_estimate = await _income_estimate_for(db, current.id, user)

    if payload.scenario_type == "category_change":
        if payload.category is None or payload.new_amount is None:
            raise HTTPException(status_code=400, detail="category and new_amount are required for category_change")
        result = simulate_category_change(income_estimate, spending_by_category, category_roles, payload.category, payload.new_amount)
    elif payload.scenario_type == "income_change":
        if payload.new_income_estimate is None:
            raise HTTPException(status_code=400, detail="new_income_estimate is required for income_change")
        result = simulate_income_change(income_estimate, payload.new_income_estimate, spending_by_category, category_roles)
    elif payload.scenario_type == "one_time_expense":
        if payload.amount is None:
            raise HTTPException(status_code=400, detail="amount is required for one_time_expense")
        result = simulate_one_time_expense(income_estimate, spending_by_category, category_roles, payload.amount)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown scenario_type: {payload.scenario_type}")

    return result.to_dict()
