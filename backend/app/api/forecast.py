import calendar
from datetime import date

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.ml.forecasting import forecast_spend
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.misc import ForecastResponse

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("", response_model=ForecastResponse)
async def get_forecast(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    today = date.today()
    month_start = today.replace(day=1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    month_end = today.replace(day=last_day)
    days_remaining = (month_end - today).days

    result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == current.id,
            Transaction.date >= month_start,
            Transaction.date <= today,
            Transaction.amount < 0,
        )
    )
    txns = result.scalars().all()

    daily_totals: dict[date, float] = {}
    for t in txns:
        daily_totals[t.date] = daily_totals.get(t.date, 0) + abs(float(t.amount))

    daily_spend = [{"date": d, "amount": amt} for d, amt in sorted(daily_totals.items())]

    forecast_result = forecast_spend(daily_spend, days_remaining, month_end)

    user_result = await db.execute(select(User).where(User.id == current.id))
    user = user_result.scalar_one_or_none()
    ceiling = float(user.spend_ceiling) if user and user.spend_ceiling else None

    on_track = forecast_result["month_end_projection"] <= ceiling if ceiling else True

    return ForecastResponse(
        points=forecast_result["points"],
        month_end_projection=forecast_result["month_end_projection"],
        ceiling=ceiling,
        on_track=on_track,
        days_remaining=days_remaining,
    )
