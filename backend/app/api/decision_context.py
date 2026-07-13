import calendar
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget
from app.models.recurring_expense import RecurringExpense
from app.models.transaction import Transaction
from app.models.user import User
from app.services.affordability_service import calculate_safe_to_spend


async def build_decision_context(db: AsyncSession, user_id) -> dict:
    today = date.today()
    month_start = today.replace(day=1)
    month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    txns = (
        await db.execute(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.date >= month_start,
                Transaction.date <= today,
                Transaction.is_ignored == False,  # noqa: E712
            )
        )
    ).scalars().all()
    spend_txns = [t for t in txns if float(t.amount) < 0]
    mtd_spend = sum(abs(float(t.amount)) for t in spend_txns)
    elapsed_days = max((today - month_start).days + 1, 1)
    month_days = calendar.monthrange(today.year, today.month)[1]
    month_end_forecast = round((mtd_spend / elapsed_days) * month_days, 2) if mtd_spend else 0

    bills = (
        await db.execute(
            select(RecurringExpense).where(
                RecurringExpense.user_id == user_id,
                RecurringExpense.next_expected_date >= today,
                RecurringExpense.next_expected_date <= month_end,
            )
        )
    ).scalars().all()
    upcoming_bills = round(sum(float(b.amount) for b in bills), 2)
    ceiling = float(user.spend_ceiling) if user and user.spend_ceiling is not None else None
    monthly_income = float(user.monthly_income) if user and user.monthly_income is not None else None
    buffer_pct = float(user.buffer_pct) if user else 0.1
    safe = calculate_safe_to_spend(
        today=today,
        month_to_date_spend=mtd_spend,
        spending_ceiling=ceiling,
        monthly_income=monthly_income,
        buffer_pct=buffer_pct,
        upcoming_bills=upcoming_bills,
    )

    budget = (
        await db.execute(select(Budget).where(Budget.user_id == user_id, Budget.month == month_start))
    ).scalar_one_or_none()
    allocations = budget.allocations if budget else {}
    category_spend: dict[str, float] = {}
    for txn in spend_txns:
        cat = txn.nudge_category or "Other"
        category_spend[cat] = category_spend.get(cat, 0) + abs(float(txn.amount))

    risk_category = None
    worst_ratio = 0.0
    for cat, alloc in allocations.items():
        allocated = float(alloc.get("allocated", 0) or 0)
        spent = category_spend.get(cat, 0)
        ratio = spent / allocated if allocated else (1.5 if spent else 0)
        if ratio > worst_ratio:
            worst_ratio = ratio
            risk_category = cat

    if not safe["can_calculate"]:
        health = "Needs setup"
        action = "Connect a bank account or upload a statement to calculate your safe-to-spend amount."
    elif safe["remaining_safe_money"] <= 0:
        health = "Tight"
        action = "Pause flexible spending today or rebalance your budget."
    elif ceiling and month_end_forecast > ceiling:
        health = "At risk"
        action = "Reduce flexible spending or move money from a lower-priority category."
    else:
        health = "On track"
        action = f"Keep today's spending under ${safe['safe_to_spend_today']:.0f}."

    return {
        "today": today,
        "user": user,
        "transactions": txns,
        "budget": budget,
        "allocations": allocations,
        "category_spend": category_spend,
        "month_to_date_spending": round(mtd_spend, 2),
        "month_end_forecast": month_end_forecast,
        "spending_ceiling": safe["spending_ceiling"],
        "upcoming_bills_total": upcoming_bills,
        "safe": safe,
        "budget_health": health,
        "top_risk_category": risk_category,
        "recommended_action": action,
    }
