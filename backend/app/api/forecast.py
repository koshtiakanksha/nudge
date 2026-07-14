import calendar
from datetime import date, timedelta

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

TRAINING_LOOKBACK_DAYS = 90


@router.get("", response_model=ForecastResponse)
async def get_forecast(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    today = date.today()
    month_start = today.replace(day=1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    month_end = today.replace(day=last_day)
    days_remaining = (month_end - today).days

    # Training window is a broad lookback, NOT limited to the current
    # month -- early in a month there simply aren't enough days elapsed
    # yet for Prophet to fit on (it needs >= 14), so restricting the
    # model's training data to "days so far this month" meant it could
    # never actually run for roughly the first two weeks of every month,
    # regardless of how much real history existed. Month-to-date actual
    # spend is computed separately below and isn't affected by how far
    # back the training window reaches.
    lookback_start = today - timedelta(days=TRAINING_LOOKBACK_DAYS)
    result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == current.id,
            Transaction.date >= lookback_start,
            Transaction.date <= today,
            Transaction.amount < 0,
        )
    )
    txns = result.scalars().all()

    daily_totals: dict[date, float] = {}
    for t in txns:
        daily_totals[t.date] = daily_totals.get(t.date, 0) + abs(float(t.amount))

    daily_spend = [{"date": d, "amount": amt} for d, amt in sorted(daily_totals.items())]
    already_spent_this_month = sum(amt for d, amt in daily_totals.items() if d >= month_start)

    forecast_result = forecast_spend(daily_spend, days_remaining, month_end, already_spent_this_month)

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
        model_used=forecast_result["model_used"],
    )
