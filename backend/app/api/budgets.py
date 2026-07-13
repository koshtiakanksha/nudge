from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.budget import BudgetAdjustRequest, BudgetGenerateRequest, BudgetOut
from app.services.claude_service import claude_service

router = APIRouter(prefix="/budgets", tags=["budgets"])


def _month_start(d: date) -> date:
    return d.replace(day=1)


async def _historical_spend_by_category(db: AsyncSession, user_id, months: int = 3) -> dict[str, float]:
    cutoff = date.today() - relativedelta(months=months)
    result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.date >= cutoff,
            Transaction.amount < 0,
        )
    )
    txns = result.scalars().all()

    totals: dict[str, float] = {}
    for t in txns:
        cat = t.nudge_category or "Other"
        totals[cat] = totals.get(cat, 0) + abs(float(t.amount))

    # average per month
    return {cat: round(total / months, 2) for cat, total in totals.items()}


@router.post("/generate", response_model=BudgetOut)
async def generate_budget(
    payload: BudgetGenerateRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_result = await db.execute(select(User).where(User.id == current.id))
    user = user_result.scalar_one_or_none()
    if user is None or user.monthly_income is None:
        raise HTTPException(status_code=400, detail="Complete onboarding (set monthly income) before generating a budget")

    month = _month_start(payload.month or date.today())

    existing_result = await db.execute(
        select(Budget).where(Budget.user_id == current.id, Budget.month == month)
    )
    existing = existing_result.scalar_one_or_none()
    if existing and not payload.regenerate:
        return _to_budget_out(existing)

    spending_history = await _historical_spend_by_category(db, current.id)
    non_negotiables = ["Utilities & Bills", "Health & Fitness"]  # MVP default; could be user-configurable

    ai_result = claude_service.generate_budget(
        monthly_income=float(user.monthly_income),
        spend_ceiling=float(user.spend_ceiling) if user.spend_ceiling else None,
        buffer_pct=float(user.buffer_pct),
        spending_by_category=spending_history,
        non_negotiables=non_negotiables,
    )

    total_allocated = sum(v["allocated"] for v in ai_result["allocations"].values())

    if existing:
        existing.allocations = ai_result["allocations"]
        existing.buffer_reserved = ai_result["buffer_reserved"]
        existing.total_allocated = total_allocated
        existing.ai_reasoning = ai_result["reasoning"]
        budget = existing
    else:
        budget = Budget(
            user_id=current.id,
            month=month,
            allocations=ai_result["allocations"],
            buffer_reserved=ai_result["buffer_reserved"],
            total_allocated=total_allocated,
            generated_by_ai=True,
            ai_reasoning=ai_result["reasoning"],
        )
        db.add(budget)

    await db.commit()
    await db.refresh(budget)
    return _to_budget_out(budget)


@router.get("/current", response_model=BudgetOut)
async def get_current_budget(
    current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    month = _month_start(date.today())
    result = await db.execute(select(Budget).where(Budget.user_id == current.id, Budget.month == month))
    budget = result.scalar_one_or_none()
    if budget is None:
        raise HTTPException(status_code=404, detail="No budget generated yet for this month")
    return _to_budget_out(budget)


@router.post("/adjust", response_model=BudgetOut)
async def adjust_budget(
    payload: BudgetAdjustRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    month = _month_start(date.today())
    result = await db.execute(select(Budget).where(Budget.user_id == current.id, Budget.month == month))
    budget = result.scalar_one_or_none()
    if budget is None:
        raise HTTPException(status_code=404, detail="No budget found for this month")

    allocations = dict(budget.allocations)
    if payload.category not in allocations:
        allocations[payload.category] = {"allocated": 0, "spent": 0, "is_non_neg": False}

    allocations[payload.category]["allocated"] = payload.new_allocated
    budget.allocations = allocations
    budget.total_allocated = sum(v["allocated"] for v in allocations.values())
    budget.generated_by_ai = False  # user override

    await db.commit()
    await db.refresh(budget)
    return _to_budget_out(budget)


def _to_budget_out(budget: Budget) -> BudgetOut:
    return BudgetOut(
        id=budget.id,
        month=budget.month,
        allocations=budget.allocations,
        buffer_reserved=float(budget.buffer_reserved),
        total_allocated=float(budget.total_allocated),
        generated_by_ai=budget.generated_by_ai,
        ai_reasoning=budget.ai_reasoning,
    )
