"""
Anomaly detector implementations used for benchmarking against the
Isolation Forest actually served in production
(see app/ml/anomaly_detection.py).

Every model implements the same interface:

    fit_predict(df: pd.DataFrame) -> np.ndarray[bool], np.ndarray[float]

df must already have the engineered features used in production:
amount_abs, day_of_week, merchant_avg, deviation_from_merchant_avg
(see app/ml/evaluation/anomaly_eval.py::_engineer_features). Returns a
boolean flagged-or-not array and a continuous anomaly score (higher =
more anomalous), so ranking and thresholding can both be scored.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


FEATURE_COLS = ["amount_abs", "day_of_week", "deviation_from_merchant_avg"]


class IsolationForestDetector:
    """Same model and features as production (app/ml/anomaly_detection.py),
    reimplemented here so it can be scored side by side with alternatives
    on labeled data — production code has no labels to check itself against."""

    name = "isolation_forest"

    def __init__(self, contamination: float = 0.08):
        self.contamination = contamination

    def fit_predict(self, df: pd.DataFrame):
        from sklearn.ensemble import IsolationForest

        X = df[FEATURE_COLS].fillna(0)
        model = IsolationForest(contamination=self.contamination, random_state=42, n_estimators=150)
        raw = model.fit_predict(X)
        scores = -model.decision_function(X)
        return raw == -1, scores


class RobustZScoreDetector:
    """Median Absolute Deviation (MAD) based z-score on transaction amount.
    Unlike a plain mean/std z-score, MAD isn't dragged around by the
    anomalies themselves, which is the point of "robust" here — a handful
    of $900 outliers in the training window shouldn't inflate the
    threshold and mask themselves."""

    name = "robust_zscore"

    def __init__(self, threshold: float = 3.5):
        self.threshold = threshold

    def fit_predict(self, df: pd.DataFrame):
        x = df["amount_abs"].to_numpy()
        median = np.median(x)
        mad = np.median(np.abs(x - median)) or 1e-6
        # 0.6745 rescales MAD to be comparable to a standard deviation
        # under a normal distribution, the standard convention.
        modified_z = 0.6745 * (x - median) / mad
        flagged = np.abs(modified_z) > self.threshold
        return flagged, np.abs(modified_z)


class LOFDetector:
    """Local Outlier Factor — density-based rather than tree-based, catches
    a different failure mode than Isolation Forest: a transaction that's
    unremarkable in isolation but sits far from its local neighborhood in
    feature space (e.g. a mid-size charge on a day full of $0 activity)."""

    name = "local_outlier_factor"

    def __init__(self, contamination: float = 0.08, n_neighbors: int = 20):
        self.contamination = contamination
        self.n_neighbors = n_neighbors

    def fit_predict(self, df: pd.DataFrame):
        from sklearn.neighbors import LocalOutlierFactor

        X = df[FEATURE_COLS].fillna(0)
        n_neighbors = min(self.n_neighbors, max(2, len(df) - 1))
        model = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=self.contamination)
        raw = model.fit_predict(X)
        scores = -model.negative_outlier_factor_
        return raw == -1, scores


class RuleBasedDetector:
    """No ML: flag if amount exceeds a household-level percentile OR is a
    large multiple of that merchant's own typical spend. This is the
    baseline every ML model needs to justify its complexity against — if
    it can't beat two hand-written rules, it isn't earning its place."""

    name = "rule_based"

    def __init__(self, percentile: float = 95.0, merchant_multiple: float = 3.0):
        self.percentile = percentile
        self.merchant_multiple = merchant_multiple

    def fit_predict(self, df: pd.DataFrame):
        amount_cutoff = float(np.percentile(df["amount_abs"], self.percentile))
        merchant_cutoff = df["merchant_avg"] * self.merchant_multiple
        flagged = (df["amount_abs"] > amount_cutoff) | (df["amount_abs"] > merchant_cutoff)
        # Score: how far past whichever cutoff applied, normalized.
        safe_amount_cutoff = max(amount_cutoff, 1e-6)
        safe_merchant_cutoff = merchant_cutoff.clip(lower=1e-6)
        score = np.maximum(
            df["amount_abs"] / safe_amount_cutoff,
            df["amount_abs"] / safe_merchant_cutoff,
        )
        return flagged.to_numpy(), score.to_numpy()


ALL_DETECTORS = {
    "isolation_forest": IsolationForestDetector,
    "robust_zscore": RobustZScoreDetector,
    "local_outlier_factor": LOFDetector,
    "rule_based": RuleBasedDetector,
}
