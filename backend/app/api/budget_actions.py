import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.decision_context import build_decision_context
from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.budget import Budget
from app.models.budget_category import BudgetCategory
from app.schemas.affordability import BudgetCategoryOut, BudgetCategoryRequest, RebalanceOut, RebalanceRequest

router = APIRouter(prefix="/budget", tags=["budget-actions"])


@router.get("/categories", response_model=list[BudgetCategoryOut])
async def list_budget_categories(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _ensure_categories(db, current.id)
    result = await db.execute(select(BudgetCategory).where(BudgetCategory.user_id == current.id).order_by(BudgetCategory.created_at.asc()))
    return [_cat_out(c) for c in result.scalars().all()]


@router.post("/categories", response_model=BudgetCategoryOut)
async def create_budget_category(payload: BudgetCategoryRequest, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cat = BudgetCategory(user_id=current.id, name=payload.name, monthly_limit=payload.monthly_limit, category_type=payload.category_type, is_disabled=payload.is_disabled, is_default=payload.is_default)
    db.add(cat)
    await _update_current_budget_allocation(db, current.id, payload.name, payload.monthly_limit, payload.is_disabled)
    await db.commit()
    await db.refresh(cat)
    return _cat_out(cat)


@router.patch("/categories/{category_id}", response_model=BudgetCategoryOut)
async def update_budget_category(category_id: uuid.UUID, payload: BudgetCategoryRequest, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BudgetCategory).where(BudgetCategory.id == category_id, BudgetCategory.user_id == current.id))
    cat = result.scalar_one_or_none()
    if cat is None:
        raise HTTPException(status_code=404, detail="Budget category not found")
    old_name = cat.name
    cat.name = payload.name
    cat.monthly_limit = payload.monthly_limit
    cat.category_type = payload.category_type
    cat.is_disabled = payload.is_disabled
    cat.is_default = payload.is_default
    await _rename_current_budget_allocation(db, current.id, old_name, payload.name, payload.monthly_limit, payload.is_disabled)
    await db.commit()
    await db.refresh(cat)
    return _cat_out(cat)


@router.delete("/categories/{category_id}")
async def delete_budget_category(category_id: uuid.UUID, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BudgetCategory).where(BudgetCategory.id == category_id, BudgetCategory.user_id == current.id))
    cat = result.scalar_one_or_none()
    if cat is None:
        raise HTTPException(status_code=404, detail="Budget category not found")
    await _update_current_budget_allocation(db, current.id, cat.name, 0, True)
    await db.delete(cat)
    await db.commit()
    return {"deleted": True}


@router.post("/rebalance", response_model=RebalanceOut)
async def rebalance_budget(payload: RebalanceRequest, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _ensure_categories(db, current.id)
    result = await db.execute(select(BudgetCategory).where(BudgetCategory.user_id == current.id))
    cats = {c.name: c for c in result.scalars().all()}
    amount = max(float(payload.amount), 0)
    message = "No change made."
    safe_change = 0.0
    if payload.action == "move_money" and payload.from_category and payload.from_category in cats and payload.to_category in cats:
        cats[payload.from_category].monthly_limit = max(float(cats[payload.from_category].monthly_limit) - amount, 0)
        cats[payload.to_category].monthly_limit = float(cats[payload.to_category].monthly_limit) + amount
        message = f"Moved ${amount:.0f} from {payload.from_category} to {payload.to_category}."
    elif payload.action == "increase_total_budget" and payload.to_category in cats:
        cats[payload.to_category].monthly_limit = float(cats[payload.to_category].monthly_limit) + amount
        message = f"Increased {payload.to_category} by ${amount:.0f}."
    elif payload.action == "reduce_future_safe_to_spend":
        safe_change = -amount
        message = f"Reduced future safe-to-spend by ${amount:.0f} this month."
    elif payload.action == "one_time_exception":
        message = f"Marked ${amount:.0f} in {payload.to_category} as a one-time exception."
    elif payload.action == "ignore_this_month":
        message = "Ignored this overage for this month."

    await _sync_budget_from_categories(db, current.id, list(cats.values()))
    await db.commit()
    updated = await list_budget_categories(current, db)
    return RebalanceOut(message=message, safe_to_spend_change=safe_change, updated_categories=updated)


async def _ensure_categories(db: AsyncSession, user_id) -> None:
    existing = (await db.execute(select(BudgetCategory).where(BudgetCategory.user_id == user_id))).scalars().all()
    if existing:
        return
    ctx = await build_decision_context(db, user_id)
    for name, alloc in ctx["allocations"].items():
        db.add(BudgetCategory(user_id=user_id, name=name, monthly_limit=float(alloc.get("allocated", 0) or 0), category_type="fixed" if alloc.get("is_non_neg") else "flexible", is_default=True))
    await db.flush()


async def _current_budget(db: AsyncSession, user_id) -> Budget | None:
    return (await db.execute(select(Budget).where(Budget.user_id == user_id, Budget.month == date.today().replace(day=1)))).scalar_one_or_none()


async def _update_current_budget_allocation(db: AsyncSession, user_id, name: str, amount: float, disabled: bool) -> None:
    budget = await _current_budget(db, user_id)
    if not budget:
        return
    allocations = dict(budget.allocations or {})
    allocations[name] = {"allocated": 0 if disabled else amount, "spent": allocations.get(name, {}).get("spent", 0), "is_non_neg": False}
    budget.allocations = allocations
    budget.total_allocated = sum(float(v.get("allocated", 0) or 0) for v in allocations.values())


async def _rename_current_budget_allocation(db: AsyncSession, user_id, old_name: str, new_name: str, amount: float, disabled: bool) -> None:
    budget = await _current_budget(db, user_id)
    if not budget:
        return
    allocations = dict(budget.allocations or {})
    old = allocations.pop(old_name, {"spent": 0, "is_non_neg": False})
    allocations[new_name] = {"allocated": 0 if disabled else amount, "spent": old.get("spent", 0), "is_non_neg": old.get("is_non_neg", False)}
    budget.allocations = allocations
    budget.total_allocated = sum(float(v.get("allocated", 0) or 0) for v in allocations.values())


async def _sync_budget_from_categories(db: AsyncSession, user_id, cats: list[BudgetCategory]) -> None:
    budget = await _current_budget(db, user_id)
    if not budget:
        return
    existing = dict(budget.allocations or {})
    budget.allocations = {
        c.name: {
            "allocated": 0 if c.is_disabled else float(c.monthly_limit),
            "spent": existing.get(c.name, {}).get("spent", 0),
            "is_non_neg": c.category_type == "fixed",
        }
        for c in cats
    }
    budget.total_allocated = sum(float(v.get("allocated", 0) or 0) for v in budget.allocations.values())


def _cat_out(c: BudgetCategory) -> BudgetCategoryOut:
    return BudgetCategoryOut(id=c.id, name=c.name, monthly_limit=float(c.monthly_limit), category_type=c.category_type, is_disabled=c.is_disabled, is_default=c.is_default)
