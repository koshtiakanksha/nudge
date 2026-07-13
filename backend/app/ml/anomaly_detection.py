"""
Anomaly detection over a user's transaction history using Isolation Forest.

Features per transaction: amount, day-of-week, merchant frequency, and
deviation from that merchant's historical average. Falls back to a simple
z-score rule if scikit-learn isn't available or history is too small.
"""
import numpy as np
import pandas as pd

MIN_TRANSACTIONS_FOR_ML = 20


def detect_anomalies(transactions: list[dict]) -> list[dict]:
    """
    transactions: [{"id": uuid, "amount": float, "date": date, "merchant_name": str}]
    Returns the subset flagged anomalous, each with an added "anomaly_score"
    (higher = more anomalous) and "typical_amount" for that merchant.
    """
    if len(transactions) < 5:
        return []

    df = pd.DataFrame(transactions)
    df["amount_abs"] = df["amount"].abs()
    df["date"] = pd.to_datetime(df["date"])
    df["day_of_week"] = df["date"].dt.dayofweek

    merchant_avg = df.groupby("merchant_name")["amount_abs"].transform("mean")
    df["merchant_avg"] = merchant_avg
    df["deviation_from_merchant_avg"] = df["amount_abs"] - df["merchant_avg"]

    if len(df) < MIN_TRANSACTIONS_FOR_ML:
        return _zscore_fallback(df)

    try:
        return _isolation_forest(df)
    except ImportError:
        return _zscore_fallback(df)


def _isolation_forest(df: pd.DataFrame) -> list[dict]:
    from sklearn.ensemble import IsolationForest

    features = df[["amount_abs", "day_of_week", "deviation_from_merchant_avg"]].fillna(0)

    model = IsolationForest(contamination=0.08, random_state=42, n_estimators=150)
    df["raw_score"] = model.fit_predict(features)
    df["anomaly_score"] = -model.decision_function(features)  # higher = more anomalous

    anomalies = df[df["raw_score"] == -1].copy()
    anomalies = anomalies.sort_values("anomaly_score", ascending=False)

    return [
        {
            "id": row["id"],
            "amount": row["amount"],
            "merchant_name": row["merchant_name"],
            "anomaly_score": round(float(row["anomaly_score"]), 4),
            "typical_amount": round(float(row["merchant_avg"]), 2),
        }
        for _, row in anomalies.iterrows()
    ]


def _zscore_fallback(df: pd.DataFrame) -> list[dict]:
    mean = df["amount_abs"].mean()
    std = df["amount_abs"].std() or 1.0
    df["zscore"] = (df["amount_abs"] - mean) / std

    anomalies = df[df["zscore"].abs() > 2.0].copy()
    anomalies = anomalies.sort_values("zscore", ascending=False)

    return [
        {
            "id": row["id"],
            "amount": row["amount"],
            "merchant_name": row["merchant_name"],
            "anomaly_score": round(float(abs(row["zscore"])) / 4, 4),  # normalize roughly to 0-1ish
            "typical_amount": round(float(row["merchant_avg"]), 2),
        }
        for _, row in anomalies.iterrows()
    ]
