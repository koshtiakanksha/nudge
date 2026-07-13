"""
Evaluates anomaly detectors against labeled synthetic transactions.

The label distinction matters and is scored separately: "unusual" is a
real but atypical purchase (a big grocery run); "fraud" is an unfamiliar
merchant with a pattern inconsistent with the household's history. A
detector that flags both equally isn't wrong, but a detector that could
*separate* them would let the product downgrade "unusual" to a nudge and
escalate "fraud" to a real alert — which app/ml/anomaly_detection.py
currently cannot do, since it has no fraud-specific features (merchant
familiarity, geography). That gap is called out explicitly in the report
rather than glossed over.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.ml.evaluation.anomaly_models import ALL_DETECTORS
from app.ml.evaluation.synthetic_data import HOUSEHOLD_PROFILES, generate_labeled_transactions


def _engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Mirrors the feature engineering in app/ml/anomaly_detection.py so
    every detector under test sees exactly what production sees."""
    df = df.copy()
    df["amount_abs"] = df["amount"].abs()
    df["date"] = pd.to_datetime(df["date"])
    df["day_of_week"] = df["date"].dt.dayofweek
    merchant_avg = df.groupby("merchant_name")["amount_abs"].transform("mean")
    df["merchant_avg"] = merchant_avg
    df["deviation_from_merchant_avg"] = df["amount_abs"] - df["merchant_avg"]
    return df


@dataclass
class RunResult:
    model: str
    profile: str
    seed: int
    precision: float
    recall: float
    f1: float
    false_alert_rate: float  # FP / total normal transactions
    n_flagged: int
    n_actual_anomalous: int
    pct_flagged_that_were_fraud: float  # of what got flagged, how much was the dangerous class
    pct_fraud_caught: float  # recall computed on fraud alone


@dataclass
class AnomalyBenchmarkReport:
    results: list[RunResult] = field(default_factory=list)

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([r.__dict__ for r in self.results])

    def summary(self) -> pd.DataFrame:
        df = self.to_dataframe()
        if df.empty:
            return df
        return (
            df.groupby(["profile", "model"])
            .agg(
                precision=("precision", "mean"), recall=("recall", "mean"), f1=("f1", "mean"),
                false_alert_rate=("false_alert_rate", "mean"),
                pct_fraud_caught=("pct_fraud_caught", "mean"),
                n_runs=("f1", "count"),
            )
            .reset_index()
            .sort_values(["profile", "f1"], ascending=[True, False])
        )


def _score_run(df: pd.DataFrame, flagged: np.ndarray) -> dict:
    actual_anomalous = df["label"].isin(["unusual", "fraud"]).to_numpy()
    actual_fraud = (df["label"] == "fraud").to_numpy()
    actual_normal = df["label"].eq("normal").to_numpy()

    tp = np.sum(flagged & actual_anomalous)
    fp = np.sum(flagged & ~actual_anomalous)
    fn = np.sum(~flagged & actual_anomalous)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    false_alert_rate = fp / actual_normal.sum() if actual_normal.sum() > 0 else 0.0

    fraud_caught = np.sum(flagged & actual_fraud)
    pct_fraud_caught = fraud_caught / actual_fraud.sum() if actual_fraud.sum() > 0 else float("nan")
    pct_flagged_that_were_fraud = (
        np.sum(flagged & actual_fraud) / flagged.sum() if flagged.sum() > 0 else 0.0
    )

    return dict(
        precision=precision, recall=recall, f1=f1, false_alert_rate=false_alert_rate,
        n_flagged=int(flagged.sum()), n_actual_anomalous=int(actual_anomalous.sum()),
        pct_flagged_that_were_fraud=pct_flagged_that_were_fraud, pct_fraud_caught=pct_fraud_caught,
    )


def run_anomaly_benchmark(
    profile: str,
    n_days: int = 120,
    seeds: list[int] | None = None,
    include_models: list[str] | None = None,
) -> AnomalyBenchmarkReport:
    seeds = seeds or [1, 2, 3]
    model_names = include_models or list(ALL_DETECTORS.keys())
    report = AnomalyBenchmarkReport()

    for seed in seeds:
        raw = generate_labeled_transactions(profile, start_date="2025-01-01", n_days=n_days, seed=seed)
        df = _engineer_features(raw)

        for name in model_names:
            try:
                detector = ALL_DETECTORS[name]()
                flagged, _scores = detector.fit_predict(df)
                metrics = _score_run(df, np.asarray(flagged))
                report.results.append(RunResult(model=name, profile=profile, seed=seed, **metrics))
            except ImportError:
                report.results.append(RunResult(
                    model=f"{name}_UNAVAILABLE", profile=profile, seed=seed,
                    precision=float("nan"), recall=float("nan"), f1=float("nan"),
                    false_alert_rate=float("nan"), n_flagged=0, n_actual_anomalous=0,
                    pct_flagged_that_were_fraud=float("nan"), pct_fraud_caught=float("nan"),
                ))

    return report


def run_full_anomaly_benchmark(profiles: list[str] | None = None, **kwargs) -> AnomalyBenchmarkReport:
    profiles = profiles or list(HOUSEHOLD_PROFILES.keys())
    combined = AnomalyBenchmarkReport()
    for profile in profiles:
        r = run_anomaly_benchmark(profile=profile, **kwargs)
        combined.results.extend(r.results)
    return combined
