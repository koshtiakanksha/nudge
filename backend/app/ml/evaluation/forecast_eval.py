"""
Rolling-origin cross-validation harness for spend forecasting.

Why rolling-origin and not a single train/test split: a single split tells
you how the model does on one particular month. Rolling-origin re-fits at
several points in time and scores each one, which is what actually answers
"how reliable is this in production, where it refits every day."

Usage:
    from app.ml.evaluation.forecast_eval import run_forecast_benchmark
    results = run_forecast_benchmark(profile="steady_earner", n_days=180)
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.ml.evaluation.forecast_models import ALL_MODELS
from app.ml.evaluation.synthetic_data import generate_daily_spend, HOUSEHOLD_PROFILES


@dataclass
class FoldResult:
    model: str
    profile: str
    fold_start: str
    mae: float
    rmse: float
    mape: float
    wape: float
    coverage: float | None  # fraction of actuals within predicted interval, if model supports one


@dataclass
class BenchmarkReport:
    fold_results: list[FoldResult] = field(default_factory=list)

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([r.__dict__ for r in self.fold_results])

    def summary(self) -> pd.DataFrame:
        df = self.to_dataframe()
        if df.empty:
            return df
        return (
            df.groupby(["profile", "model"])
            .agg(mae=("mae", "mean"), rmse=("rmse", "mean"), mape=("mape", "mean"),
                 wape=("wape", "mean"), coverage=("coverage", "mean"), n_folds=("mae", "count"))
            .reset_index()
            .sort_values(["profile", "wape"])
        )


def _metrics(actual: np.ndarray, predicted: np.ndarray) -> dict:
    err = actual - predicted
    mae = np.mean(np.abs(err))
    rmse = np.sqrt(np.mean(err ** 2))
    # MAPE undefined at actual == 0; guard and report WAPE as the primary
    # scale-free metric since daily spend legitimately hits $0.
    nonzero = actual != 0
    mape = np.mean(np.abs(err[nonzero] / actual[nonzero])) * 100 if nonzero.any() else float("nan")
    wape = np.sum(np.abs(err)) / np.sum(np.abs(actual)) * 100 if np.sum(np.abs(actual)) > 0 else float("nan")
    return dict(mae=mae, rmse=rmse, mape=mape, wape=wape)


def run_forecast_benchmark(
    profile: str,
    n_days: int = 180,
    horizon: int = 7,
    n_folds: int = 6,
    min_train_days: int = 30,
    include_models: list[str] | None = None,
    include_prophet: bool = True,
    seed: int = 42,
) -> BenchmarkReport:
    """
    Generates n_days of synthetic history for `profile`, then walks forward
    through n_folds rolling-origin folds. Each fold trains on everything up
    to fold_start and scores the next `horizon` days.
    """
    data = generate_daily_spend(profile, start_date="2025-01-01", n_days=n_days, seed=seed)
    model_names = include_models or list(ALL_MODELS.keys())

    fold_starts = np.linspace(min_train_days, n_days - horizon - 1, n_folds, dtype=int)

    report = BenchmarkReport()

    for fold_start_idx in fold_starts:
        train = data.iloc[:fold_start_idx].reset_index(drop=True)
        test = data.iloc[fold_start_idx: fold_start_idx + horizon].reset_index(drop=True)
        if len(test) < horizon or len(train) < min_train_days:
            continue
        actual = test["amount"].to_numpy()
        fold_label = str(pd.to_datetime(train["date"].iloc[-1]).date())

        for name in model_names:
            try:
                model = ALL_MODELS[name]()
                preds = model.fit_predict(train, horizon)
                m = _metrics(actual, preds)

                coverage = None
                if hasattr(model, "fit_predict_interval"):
                    _, lower, upper = model.fit_predict_interval(train, horizon)
                    coverage = float(np.mean((actual >= lower) & (actual <= upper)))

                report.fold_results.append(FoldResult(
                    model=name, profile=profile, fold_start=fold_label,
                    coverage=coverage, **m,
                ))
            except ImportError:
                report.fold_results.append(FoldResult(
                    model=f"{name}_UNAVAILABLE", profile=profile, fold_start=fold_label,
                    mae=float("nan"), rmse=float("nan"), mape=float("nan"),
                    wape=float("nan"), coverage=None,
                ))

        if include_prophet:
            try:
                from app.ml.forecasting import _prophet_forecast
                pf = _prophet_forecast(train, horizon, month_end_date=test["date"].max())
                preds = np.array([p["predicted_spend"] for p in pf["points"]])[:horizon]
                lower = np.array([p["lower_bound"] for p in pf["points"]])[:horizon]
                upper = np.array([p["upper_bound"] for p in pf["points"]])[:horizon]
                if len(preds) == horizon:
                    m = _metrics(actual, preds)
                    coverage = float(np.mean((actual >= lower) & (actual <= upper)))
                    report.fold_results.append(FoldResult(
                        model="prophet", profile=profile, fold_start=fold_label,
                        coverage=coverage, **m,
                    ))
            except Exception:
                report.fold_results.append(FoldResult(
                    model="prophet_UNAVAILABLE", profile=profile, fold_start=fold_label,
                    mae=float("nan"), rmse=float("nan"), mape=float("nan"),
                    wape=float("nan"), coverage=None,
                ))

    return report


def run_full_benchmark(profiles: list[str] | None = None, **kwargs) -> BenchmarkReport:
    """Runs run_forecast_benchmark across every household profile and
    concatenates the results, so the summary shows whether a model wins
    everywhere or only on one spending shape."""
    profiles = profiles or list(HOUSEHOLD_PROFILES.keys())
    combined = BenchmarkReport()
    for profile in profiles:
        r = run_forecast_benchmark(profile=profile, **kwargs)
        combined.fold_results.extend(r.fold_results)
    return combined
