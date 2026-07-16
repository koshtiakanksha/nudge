from datetime import date

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.budget import Budget
from app.models.budget_category import BudgetCategory
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.budget import BudgetAdjustRequest, BudgetGenerateRequest, BudgetOut, BudgetSaveRequest
from app.services.budget_engine import diff_allocations
from app.services.category_role_service import is_non_negotiable, roles_for_categories
from app.services.claude_service import claude_service

router = APIRouter(prefix="/budgets", tags=["budgets"])


def _month_start(d: date) -> date:
    return d.replace(day=1)


async def _previous_month_allocations(db: AsyncSession, user_id, month: date) -> dict | None:
    prev_month = month - relativedelta(months=1)
    result = await db.execute(
        select(Budget).where(Budget.user_id == user_id, Budget.month == prev_month)
    )
    prev = result.scalar_one_or_none()
    return prev.allocations if prev else None


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


async def _month_spend_by_category(db: AsyncSession, user_id, month: date) -> dict[str, float]:
    next_month = month + relativedelta(months=1)
    result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.date >= month,
            Transaction.date < next_month,
            Transaction.amount < 0,
        )
    )
    txns = result.scalars().all()

    totals: dict[str, float] = {}
    for t in txns:
        cat = t.nudge_category or "Other"
        totals[cat] = totals.get(cat, 0) + abs(float(t.amount))
    return {cat: round(total, 2) for cat, total in totals.items()}


async def _non_negotiables_for(db: AsyncSession, user_id, spending_history: dict[str, float]) -> list[str]:
    """
    Was: a hardcoded set of 4 literal category names ({"Rent",
    "Utilities", "Utilities & Bills", "Health"}) -- it ignored whatever
    the user actually configured in Budget Categories entirely, and
    couldn't recognize a category outside that exact list no matter how
    the user set it up.

    Now: reads the user's real BudgetCategory rows (an explicit
    category_type="fixed" always wins) and falls back to name-based
    defaults (Rent, Utilities, Insurance, etc.) for categories the user
    hasn't explicitly configured yet.
    """
    result = await db.execute(select(BudgetCategory).where(BudgetCategory.user_id == user_id))
    category_types = {c.name: c.category_type for c in result.scalars().all()}
    roles = roles_for_categories(list(spending_history.keys()), category_types)
    return [cat for cat, role in roles.items() if is_non_negotiable(role)]


def _normalize_allocations(raw: dict) -> dict:
    allocations = {}
    for category, alloc in (raw or {}).items():
        name = str(category).strip()
        if not name:
            continue
        allocations[name] = {
            "allocated": max(float(alloc.get("allocated", 0) or 0), 0),
            "spent": max(float(alloc.get("spent", 0) or 0), 0),
            "is_non_neg": bool(alloc.get("is_non_neg", False)),
        }
    return allocations


async def _with_current_spend(db: AsyncSession, budget: Budget) -> Budget:
    allocations = _normalize_allocations(budget.allocations)
    spending = await _month_spend_by_category(db, budget.user_id, budget.month)
    for category, spent in spending.items():
        allocations.setdefault(category, {"allocated": 0, "spent": 0, "is_non_neg": False})
        allocations[category]["spent"] = spent
    budget.allocations = allocations
    budget.total_allocated = sum(v["allocated"] for v in allocations.values())
    return budget


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
        await _with_current_spend(db, existing)
        return await _to_budget_out(db, existing)

    spending_history = await _historical_spend_by_category(db, current.id)
    non_negotiables = await _non_negotiables_for(db, current.id, spending_history)
    previous_allocations = await _previous_month_allocations(db, current.id, month)

    ai_result = claude_service.generate_budget(
        monthly_income=float(user.monthly_income),
        spend_ceiling=float(user.spend_ceiling) if user.spend_ceiling else None,
        buffer_pct=float(user.buffer_pct),
        spending_by_category=spending_history,
        non_negotiables=non_negotiables,
        previous_allocations=previous_allocations,
    )

    total_allocated = sum(v["allocated"] for v in ai_result["allocations"].values())

    if existing:
        existing.allocations = ai_result["allocations"]
        existing.buffer_reserved = ai_result["buffer_reserved"]
        existing.total_allocated = total_allocated
        existing.ai_reasoning = ai_result["reasoning"]
        existing.engine_version = ai_result["engine_version"]
        existing.prompt_version = ai_result["prompt_version"]
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
            engine_version=ai_result["engine_version"],
            prompt_version=ai_result["prompt_version"],
        )
        db.add(budget)

    await db.commit()
    await db.refresh(budget)
    await _with_current_spend(db, budget)
    return await _to_budget_out(db, budget)


@router.get("/current", response_model=BudgetOut)
async def get_current_budget(
    current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    month = _month_start(date.today())
    result = await db.execute(select(Budget).where(Budget.user_id == current.id, Budget.month == month))
    budget = result.scalar_one_or_none()
    if budget is None:
        raise HTTPException(status_code=404, detail="No budget generated yet for this month")
    await _with_current_spend(db, budget)
    return await _to_budget_out(db, budget)


@router.put("/current", response_model=BudgetOut)
async def save_current_budget(
    payload: BudgetSaveRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    month = _month_start(payload.month or date.today())
    user_result = await db.execute(select(User).where(User.id == current.id))
    user = user_result.scalar_one_or_none()
    if user is None:
        user = User(id=current.id, email=current.email or f"{current.id}@local.test")
        db.add(user)

    if payload.monthly_income is not None:
        user.monthly_income = payload.monthly_income
    if payload.total_budget is not None:
        user.spend_ceiling = payload.total_budget
    if user.monthly_income is not None and user.spend_ceiling is not None:
        user.onboarding_complete = True

    result = await db.execute(select(Budget).where(Budget.user_id == current.id, Budget.month == month))
    budget = result.scalar_one_or_none()

    spending = await _month_spend_by_category(db, current.id, month)
    allocations = {}
    for category in payload.categories:
        name = category.name.strip()
        if not name:
            continue
        allocations[name] = {
            "allocated": max(float(category.allocated or 0), 0),
            "spent": spending.get(name, max(float(category.spent or 0), 0)),
            "is_non_neg": category.is_non_neg,
        }

    for name, spent in spending.items():
        allocations.setdefault(name, {"allocated": 0, "spent": spent, "is_non_neg": False})

    total_allocated = sum(v["allocated"] for v in allocations.values())
    buffer_reserved = max(float(user.monthly_income or 0) - float(user.spend_ceiling or total_allocated), 0)

    if budget:
        budget.allocations = allocations
        budget.buffer_reserved = buffer_reserved
        budget.total_allocated = total_allocated
        budget.generated_by_ai = False
        budget.ai_reasoning = payload.ai_reasoning
    else:
        budget = Budget(
            user_id=current.id,
            month=month,
            allocations=allocations,
            buffer_reserved=buffer_reserved,
            total_allocated=total_allocated,
            generated_by_ai=False,
            ai_reasoning=payload.ai_reasoning,
        )
        db.add(budget)

    await db.commit()
    await db.refresh(budget)
    await _with_current_spend(db, budget)
    return await _to_budget_out(db, budget)


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

    allocations = _normalize_allocations(budget.allocations)
    if payload.category not in allocations:
        allocations[payload.category] = {"allocated": 0, "spent": 0, "is_non_neg": False}

    allocations[payload.category]["allocated"] = payload.new_allocated
    budget.allocations = allocations
    budget.total_allocated = sum(v["allocated"] for v in allocations.values())
    budget.generated_by_ai = False  # user override

    await db.commit()
    await db.refresh(budget)
    await _with_current_spend(db, budget)
    return await _to_budget_out(db, budget)


async def _to_budget_out(db: AsyncSession, budget: Budget) -> BudgetOut:
    user_result = await db.execute(select(User).where(User.id == budget.user_id))
    user = user_result.scalar_one_or_none()
    previous_allocations = await _previous_month_allocations(db, budget.user_id, budget.month)
    return BudgetOut(
        id=budget.id,
        month=budget.month,
        monthly_income=float(user.monthly_income) if user and user.monthly_income is not None else None,
        total_budget=float(user.spend_ceiling) if user and user.spend_ceiling is not None else None,
        allocations=budget.allocations,
        buffer_reserved=float(budget.buffer_reserved),
        total_allocated=float(budget.total_allocated),
        generated_by_ai=budget.generated_by_ai,
        ai_reasoning=budget.ai_reasoning,
        engine_version=budget.engine_version,
        prompt_version=budget.prompt_version,
        changes_from_previous=diff_allocations(previous_allocations, budget.allocations),
    )
