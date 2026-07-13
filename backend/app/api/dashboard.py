import calendar
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.ml.forecasting import forecast_spend
from app.models.anomaly import Anomaly
from app.models.price_watch import PriceWatch
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.misc import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    today = date.today()
    month_start = today.replace(day=1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    month_end = today.replace(day=last_day)
    days_remaining = (month_end - today).days

    txn_result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == current.id,
            Transaction.date >= month_start,
            Transaction.date <= today,
        )
    )
    txns = txn_result.scalars().all()

    spend_txns = [t for t in txns if float(t.amount) < 0]
    income_txns = [t for t in txns if float(t.amount) > 0]

    mtd_spend = sum(abs(float(t.amount)) for t in spend_txns)
    mtd_income = sum(float(t.amount) for t in income_txns)

    category_totals: dict[str, float] = {}
    for t in spend_txns:
        cat = t.nudge_category or "Other"
        category_totals[cat] = category_totals.get(cat, 0) + abs(float(t.amount))
    top_categories = sorted(
        [{"category": k, "amount": round(v, 2)} for k, v in category_totals.items()],
        key=lambda x: x["amount"],
        reverse=True,
    )[:5]

    user_result = await db.execute(select(User).where(User.id == current.id))
    user = user_result.scalar_one_or_none()

    daily_totals: dict[date, float] = {}
    for t in spend_txns:
        daily_totals[t.date] = daily_totals.get(t.date, 0) + abs(float(t.amount))
    daily_spend = [{"date": d, "amount": amt} for d, amt in sorted(daily_totals.items())]
    forecast_result = forecast_spend(daily_spend, days_remaining, month_end)

    buffer_target = float(user.monthly_income) * float(user.buffer_pct) if user and user.monthly_income else 0
    buffer_status = max(0.0, min(1.0, (mtd_income - mtd_spend) / buffer_target)) if buffer_target else 1.0

    anomaly_count = (
        await db.execute(select(Anomaly).where(Anomaly.user_id == current.id, Anomaly.notified == False))  # noqa: E712
    ).scalars().all()

    watch_count = (
        await db.execute(select(PriceWatch).where(PriceWatch.user_id == current.id))
    ).scalars().all()

    return DashboardSummary(
        month_to_date_spend=round(mtd_spend, 2),
        month_to_date_income=round(mtd_income, 2),
        buffer_status=round(buffer_status, 2),
        top_categories=top_categories,
        spend_ceiling=float(user.spend_ceiling) if user and user.spend_ceiling else None,
        projected_month_end=forecast_result["month_end_projection"],
        recent_anomalies=len(anomaly_count),
        active_price_watches=len(watch_count),
    )
