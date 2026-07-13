"""
Synthetic household spending generators used to evaluate forecasting and
anomaly-detection models against ground truth we control.

Real transaction data never comes with labels ("this forecast error is
because of a holiday spike", "this transaction is genuinely fraudulent").
To report honest precision/recall/MAE numbers we generate data with a
known underlying process, so we know exactly what a correct model should
find.

Five household archetypes are defined below because a single synthetic
series would let a model overfit to one spending shape. A model that only
works on smooth, low-variance spend is not the same as one that works on
someone who gets paid biweekly and spends in bursts.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


HOUSEHOLD_PROFILES = {
    "steady_earner": dict(
        base=45.0, weekday_amp=10.0, weekend_amp=25.0, noise_std=8.0,
        monthly_bills=[(1, 1200.0), (15, 90.0)], trend_per_day=0.0,
    ),
    "biweekly_burster": dict(
        base=20.0, weekday_amp=5.0, weekend_amp=60.0, noise_std=15.0,
        monthly_bills=[(1, 1800.0), (14, 1800.0)], trend_per_day=0.0,
    ),
    "gig_variable": dict(
        base=35.0, weekday_amp=20.0, weekend_amp=20.0, noise_std=30.0,
        monthly_bills=[(3, 700.0)], trend_per_day=0.02,
    ),
    "student_low_volume": dict(
        base=15.0, weekday_amp=5.0, weekend_amp=15.0, noise_std=6.0,
        monthly_bills=[(1, 450.0)], trend_per_day=0.0,
    ),
    "high_earner_lumpy": dict(
        base=80.0, weekday_amp=15.0, weekend_amp=90.0, noise_std=40.0,
        monthly_bills=[(1, 3500.0), (20, 600.0)], trend_per_day=0.05,
    ),
}


def generate_daily_spend(
    profile: str,
    start_date: str,
    n_days: int,
    seed: int = 42,
    inject_seasonal_holiday_bump: bool = True,
) -> pd.DataFrame:
    """Returns a DataFrame with columns [date, amount] of daily total spend
    for one synthetic household over n_days, following `profile`."""
    if profile not in HOUSEHOLD_PROFILES:
        raise ValueError(f"Unknown profile '{profile}'. Options: {list(HOUSEHOLD_PROFILES)}")

    cfg = HOUSEHOLD_PROFILES[profile]
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start=start_date, periods=n_days, freq="D")

    amounts = []
    for i, d in enumerate(dates):
        is_weekend = d.dayofweek >= 5
        seasonal = cfg["weekend_amp"] if is_weekend else cfg["weekday_amp"]
        val = cfg["base"] + seasonal * rng.random() + cfg["trend_per_day"] * i
        val += rng.normal(0, cfg["noise_std"])

        for bill_day, bill_amt in cfg["monthly_bills"]:
            if d.day == bill_day:
                val += bill_amt

        if inject_seasonal_holiday_bump and d.month == 12 and 18 <= d.day <= 26:
            val *= 1.6

        amounts.append(max(0.0, round(val, 2)))

    return pd.DataFrame({"date": dates, "amount": amounts})


def generate_labeled_transactions(
    profile: str,
    start_date: str,
    n_days: int,
    avg_transactions_per_day: float = 3.0,
    anomaly_rate: float = 0.03,
    fraud_rate: float = 0.005,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Returns individual (not daily-aggregated) transactions with ground-truth
    labels, for evaluating anomaly detection.

    label column: "normal" | "unusual" | "fraud"
      - "unusual": a real but atypical purchase by the same household at a
        merchant they use (e.g. a much larger-than-normal grocery run).
      - "fraud": an unfamiliar merchant, unfamiliar geography/pattern,
        amount inconsistent with anything the household does. Meant to be
        distinguishable from "unusual" on features, not just magnitude.
    """
    cfg = HOUSEHOLD_PROFILES[profile]
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start=start_date, periods=n_days, freq="D")

    merchants = ["Grocery Co-op", "Corner Coffee", "Gas & Go", "Streamflix",
                 "Metro Transit", "Pharmacy Plus", "Takeout Kitchen"]
    merchant_typical = {m: cfg["base"] * rng.uniform(0.3, 1.8) for m in merchants}

    rows = []
    txn_id = 0
    for d in dates:
        n_txns = rng.poisson(avg_transactions_per_day)
        for _ in range(n_txns):
            txn_id += 1
            roll = rng.random()
            merchant = rng.choice(merchants)
            typical = merchant_typical[merchant]

            if roll < fraud_rate:
                amount = typical * rng.uniform(4, 12) + rng.uniform(100, 900)
                merchant = f"Unknown Merchant {rng.integers(1000, 9999)}"
                label = "fraud"
            elif roll < fraud_rate + anomaly_rate:
                amount = typical * rng.uniform(2.5, 4.5)
                label = "unusual"
            else:
                amount = max(1.0, typical * rng.uniform(0.6, 1.4) + rng.normal(0, cfg["noise_std"] * 0.2))
                label = "normal"

            rows.append({
                "id": txn_id,
                "date": d,
                "amount": -round(amount, 2),
                "merchant_name": merchant,
                "label": label,
            })

    return pd.DataFrame(rows)
