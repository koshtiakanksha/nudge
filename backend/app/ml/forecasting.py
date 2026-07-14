"""
Spend forecasting using Facebook Prophet.

Falls back to a simple linear/moving-average projection if Prophet isn't
installed or there isn't enough history yet (cold start, <14 days of data),
so the forecast endpoint always returns something useful.
"""
import logging
from datetime import date, timedelta

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

MIN_DAYS_FOR_PROPHET = 14


def forecast_spend(
    daily_spend: list[dict],  # [{"date": date, "amount": float}] -- historical training window, NOT limited to the current month
    days_remaining_in_month: int,
    month_end_date: date,
    already_spent_this_month: float,
) -> dict:
    """
    Returns:
    {
      "points": [{"date": ..., "predicted_spend": ..., "lower_bound": ..., "upper_bound": ...}],
      "month_end_projection": float,
      "model_used": "prophet" | "fallback_moving_average",
    }

    daily_spend is the training history fed to the model -- this should be
    a broad lookback window (e.g. the last 90 days), not just days elapsed
    so far in the current month. Conflating those two was the original
    bug: early in a month, "days elapsed so far" is always under
    MIN_DAYS_FOR_PROPHET, so the real model could never actually run no
    matter how much genuine history existed. already_spent_this_month is
    tracked separately and is exactly what it says -- actual month-to-date
    spend, used for the projection total, independent of how much history
    was used to train the model.
    """
    if not daily_spend:
        return {"points": [], "month_end_projection": round(already_spent_this_month, 2), "model_used": "none"}

    df = pd.DataFrame(daily_spend)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    if len(df) < MIN_DAYS_FOR_PROPHET:
        return _fallback_forecast(df, days_remaining_in_month, month_end_date, already_spent_this_month)

    try:
        return _prophet_forecast(df, days_remaining_in_month, month_end_date, already_spent_this_month)
    except Exception as exc:
        # Prophet's cmdstan backend can fail to initialize in some sandboxed
        # or read-only-filesystem environments (missing compiled binaries).
        # Fall back to the moving-average projection rather than 500ing --
        # but log it and mark it in the response, so a silently-degraded
        # forecast is visible instead of looking identical to a real one.
        logger.warning("Prophet forecast failed, falling back to moving average: %s", exc)
        return _fallback_forecast(df, days_remaining_in_month, month_end_date, already_spent_this_month)


def _prophet_forecast(df: pd.DataFrame, days_remaining: int, month_end_date: date, already_spent_this_month: float) -> dict:
    from prophet import Prophet

    prophet_df = df.rename(columns={"date": "ds", "amount": "y"})
    model = Prophet(
        daily_seasonality=False,
        weekly_seasonality=True,
        yearly_seasonality=False,
        interval_width=0.8,
    )
    model.fit(prophet_df)

    future = model.make_future_dataframe(periods=days_remaining)
    forecast = model.predict(future)

    future_only = forecast[forecast["ds"] > df["date"].max()]
    points = [
        {
            "date": row["ds"].date(),
            "predicted_spend": max(0.0, round(row["yhat"], 2)),
            "lower_bound": max(0.0, round(row["yhat_lower"], 2)),
            "upper_bound": max(0.0, round(row["yhat_upper"], 2)),
        }
        for _, row in future_only.iterrows()
    ]

    projected_remaining = sum(p["predicted_spend"] for p in points)

    return {
        "points": points,
        "month_end_projection": round(already_spent_this_month + projected_remaining, 2),
        "model_used": "prophet",
    }


def _fallback_forecast(df: pd.DataFrame, days_remaining: int, month_end_date: date, already_spent_this_month: float) -> dict:
    """Simple moving-average projection for cold-start users (<14 days history)
    or when Prophet is unavailable."""
    avg_daily = df["amount"].mean() if len(df) else 0.0
    std_daily = df["amount"].std() if len(df) > 1 else avg_daily * 0.3

    last_date = df["date"].max().date() if len(df) else month_end_date
    points = []
    for i in range(1, days_remaining + 1):
        d = last_date + timedelta(days=i)
        if d > month_end_date:
            break
        points.append(
            {
                "date": d,
                "predicted_spend": round(max(0.0, avg_daily), 2),
                "lower_bound": round(max(0.0, avg_daily - std_daily), 2),
                "upper_bound": round(avg_daily + std_daily, 2),
            }
        )

    projected_remaining = sum(p["predicted_spend"] for p in points)

    return {
        "points": points,
        "month_end_projection": round(already_spent_this_month + projected_remaining, 2),
        "model_used": "fallback_moving_average",
    }
