"""
Forecast model implementations used purely for benchmarking against
Prophet (the model actually served in production, see app/ml/forecasting.py).

Every model below implements the same tiny interface:

    fit_predict(history: pd.DataFrame, horizon: int) -> np.ndarray

history has columns [date, amount] sorted ascending. Returns an array of
`horizon` point forecasts for the next `horizon` days. Models that support
it also return a `(lower, upper)` interval array from `fit_predict_interval`;
models that don't (seasonal naive, moving average) approximate an interval
from residual spread so calibration can still be scored on equal footing.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class SeasonalNaive:
    """Predicts day t as the value observed 7 days earlier (last observed
    week repeated forward). Standard baseline for weekly-seasonal series —
    a model earns nothing for beating this by a trivial margin."""

    name = "seasonal_naive"

    def fit_predict(self, history: pd.DataFrame, horizon: int) -> np.ndarray:
        y = history["amount"].to_numpy()
        if len(y) < 7:
            return np.full(horizon, y.mean() if len(y) else 0.0)
        last_week = y[-7:]
        reps = int(np.ceil(horizon / 7))
        return np.tile(last_week, reps)[:horizon]

    def residual_std(self, history: pd.DataFrame) -> float:
        y = history["amount"].to_numpy()
        if len(y) < 14:
            return y.std() if len(y) else 1.0
        errs = y[7:] - y[:-7]
        return errs.std()

    def fit_predict_interval(self, history: pd.DataFrame, horizon: int, z: float = 1.28):
        point = self.fit_predict(history, horizon)
        spread = self.residual_std(history) * z
        return point, np.clip(point - spread, 0, None), point + spread


class MovingAverage:
    """Flat forecast at the trailing N-day mean. The floor every model
    needs to beat for cold-start users."""

    name = "moving_average"

    def __init__(self, window: int = 14):
        self.window = window

    def fit_predict(self, history: pd.DataFrame, horizon: int) -> np.ndarray:
        y = history["amount"].to_numpy()
        window = y[-self.window:] if len(y) >= self.window else y
        avg = window.mean() if len(window) else 0.0
        return np.full(horizon, avg)

    def residual_std(self, history: pd.DataFrame) -> float:
        y = history["amount"].to_numpy()
        window = y[-self.window:] if len(y) >= self.window else y
        return window.std() if len(window) > 1 else (window.mean() * 0.3 if len(window) else 1.0)

    def fit_predict_interval(self, history: pd.DataFrame, horizon: int, z: float = 1.28):
        point = self.fit_predict(history, horizon)
        spread = self.residual_std(history) * z
        return point, np.clip(point - spread, 0, None), point + spread


class ArimaModel:
    """statsmodels SARIMAX with weekly seasonal order. Requires statsmodels;
    raises ImportError if unavailable so the harness can record it as
    unavailable rather than silently skipping it."""

    name = "arima"

    def __init__(self, order=(1, 1, 1), seasonal_order=(1, 0, 1, 7)):
        self.order = order
        self.seasonal_order = seasonal_order
        self._fitted = None

    def fit_predict(self, history: pd.DataFrame, horizon: int) -> np.ndarray:
        from statsmodels.tsa.statespace.sarimax import SARIMAX

        y = history["amount"].to_numpy()
        if len(y) < 21:
            return np.full(horizon, y.mean() if len(y) else 0.0)

        model = SARIMAX(
            y, order=self.order, seasonal_order=self.seasonal_order,
            enforce_stationarity=False, enforce_invertibility=False,
        )
        self._fitted = model.fit(disp=False)
        forecast = self._fitted.get_forecast(steps=horizon)
        return np.clip(forecast.predicted_mean, 0, None)

    def fit_predict_interval(self, history: pd.DataFrame, horizon: int, alpha: float = 0.2):
        from statsmodels.tsa.statespace.sarimax import SARIMAX

        y = history["amount"].to_numpy()
        if len(y) < 21:
            flat = np.full(horizon, y.mean() if len(y) else 0.0)
            spread = y.std() if len(y) > 1 else flat.mean() * 0.3
            return flat, np.clip(flat - spread, 0, None), flat + spread

        model = SARIMAX(
            y, order=self.order, seasonal_order=self.seasonal_order,
            enforce_stationarity=False, enforce_invertibility=False,
        )
        fitted = model.fit(disp=False)
        fc = fitted.get_forecast(steps=horizon)
        ci = fc.conf_int(alpha=alpha)
        point = np.clip(fc.predicted_mean, 0, None)
        lower = np.clip(ci[:, 0], 0, None)
        upper = np.clip(ci[:, 1], 0, None)
        return point, lower, upper


class GradientBoostingForecast:
    """Gradient-boosted regressor over lag + calendar features. Represents
    the "throw ML at it" option — included specifically because it's easy
    to overrate; on short daily-spend series with few real signals it
    frequently loses to seasonal naive, which is worth demonstrating rather
    than asserting."""

    name = "gradient_boosting"
    LAGS = (1, 2, 3, 7, 14)

    def _make_features(self, y: np.ndarray, dates: pd.DatetimeIndex) -> pd.DataFrame:
        df = pd.DataFrame({"y": y, "date": dates})
        for lag in self.LAGS:
            df[f"lag_{lag}"] = df["y"].shift(lag)
        df["dow"] = df["date"].dt.dayofweek
        df["day_of_month"] = df["date"].dt.day
        return df

    def fit_predict(self, history: pd.DataFrame, horizon: int) -> np.ndarray:
        from sklearn.ensemble import GradientBoostingRegressor

        y = history["amount"].to_numpy()
        dates = pd.to_datetime(history["date"])
        if len(y) < max(self.LAGS) + 10:
            return np.full(horizon, y.mean() if len(y) else 0.0)

        feat = self._make_features(y, dates).dropna()
        feature_cols = [f"lag_{l}" for l in self.LAGS] + ["dow", "day_of_month"]
        model = GradientBoostingRegressor(random_state=42, n_estimators=150, max_depth=3)
        model.fit(feat[feature_cols], feat["y"])

        # Recursive multi-step: predict one day, append it, roll forward.
        history_vals = list(y)
        history_dates = list(dates)
        preds = []
        for _ in range(horizon):
            next_date = history_dates[-1] + pd.Timedelta(days=1)
            row = {}
            for lag in self.LAGS:
                row[f"lag_{lag}"] = history_vals[-lag]
            row["dow"] = next_date.dayofweek
            row["day_of_month"] = next_date.day
            x = pd.DataFrame([row])[feature_cols]
            pred = max(0.0, float(model.predict(x)[0]))
            preds.append(pred)
            history_vals.append(pred)
            history_dates.append(next_date)

        return np.array(preds)


ALL_MODELS = {
    "seasonal_naive": SeasonalNaive,
    "moving_average": MovingAverage,
    "arima": ArimaModel,
    "gradient_boosting": GradientBoostingForecast,
}
