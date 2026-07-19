import calendar
from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget
from app.models.plaid_item import PlaidItem
from app.models.recurring_expense import RecurringExpense
from app.models.transaction import Transaction
from app.models.user import User
from app.services.affordability_service import (
    calculate_safe_to_spend,
    project_month_end_spend,
    resolve_monthly_income,
)
from app.services.income_service import detect_income


async def build_decision_context(db: AsyncSession, user_id) -> dict:
    today = date.today()
    month_start = today.replace(day=1)
    month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    # Was: only fetched this-month transactions. Widened to 3 months so
    # detect_income() has enough history to find a recurring stream --
    # month-to-date figures below still only use the month_start-filtered
    # subset, unchanged from before.
    income_window_start = month_start - relativedelta(months=3)
    recent_txns = (
        await db.execute(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.date >= income_window_start,
                Transaction.date <= today,
                Transaction.is_ignored == False,  # noqa: E712
            )
        )
    ).scalars().all()
    txns = [t for t in recent_txns if t.date >= month_start]
    spend_txns = [t for t in txns if float(t.amount) < 0]
    mtd_spend = sum(abs(float(t.amount)) for t in spend_txns)
    elapsed_days = max((today - month_start).days + 1, 1)
    month_days = calendar.monthrange(today.year, today.month)[1]

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
    # Was: month_end_forecast = (mtd_spend / elapsed_days) * month_days,
    # ignoring upcoming_bills entirely -- inconsistent with
    # calculate_safe_to_spend's own remaining figure below, which does
    # subtract upcoming bills. A user with modest daily spend but a
    # large known bill still due this month wasn't being flagged
    # "At risk" despite the risk being real.
    month_end_forecast = project_month_end_spend(mtd_spend, elapsed_days, month_days, upcoming_bills)

    ceiling = float(user.spend_ceiling) if user and user.spend_ceiling is not None else None
    user_monthly_income = float(user.monthly_income) if user and user.monthly_income is not None else None
    # Was: safe-to-spend was blocked entirely ("Needs setup") for any
    # user without a manually-entered income, even with months of
    # transaction history to estimate from. resolve_monthly_income falls
    # back to income_service's conservative estimate when there's no
    # manual value -- manual entry still always wins when present.
    income_profile = None if user_monthly_income is not None else detect_income(recent_txns)
    monthly_income, income_source = resolve_monthly_income(user_monthly_income, income_profile)
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

    has_linked_account = (
        await db.execute(select(PlaidItem.id).where(PlaidItem.user_id == user_id).limit(1))
    ).scalar_one_or_none() is not None
    has_any_transaction = (
        await db.execute(select(Transaction.id).where(Transaction.user_id == user_id).limit(1))
    ).scalar_one_or_none() is not None
    has_linked_data = has_linked_account or has_any_transaction

    if not safe["can_calculate"]:
        health = "Needs setup"
        if has_linked_data:
            # income_source will be "unavailable" here, since
            # resolve_monthly_income already tried and failed to derive
            # an estimate from recent_txns before we got to this branch.
            action = "Not enough transaction history yet to estimate your income -- set it manually in Settings, or connect more history."
        else:
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
        "has_linked_data": has_linked_data,
        "month_to_date_spending": round(mtd_spend, 2),
        "month_end_forecast": month_end_forecast,
        "spending_ceiling": safe["spending_ceiling"],
        "upcoming_bills_total": upcoming_bills,
        "safe": safe,
        "income_source": income_source,
        "budget_health": health,
        "top_risk_category": risk_category,
        "recommended_action": action,
    }
