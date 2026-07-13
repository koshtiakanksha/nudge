from datetime import date, timedelta

from app.ml.anomaly_detection import detect_anomalies
from app.ml.forecasting import forecast_spend


def test_forecast_cold_start_fallback():
    daily_spend = [{"date": date.today() - timedelta(days=i), "amount": 50.0} for i in range(5, 0, -1)]
    result = forecast_spend(daily_spend, days_remaining_in_month=10, month_end_date=date.today() + timedelta(days=10))
    assert "points" in result
    assert result["month_end_projection"] > 0


def test_forecast_empty_data():
    result = forecast_spend([], days_remaining_in_month=10, month_end_date=date.today())
    assert result["points"] == []
    assert result["month_end_projection"] == 0.0


def test_anomaly_detection_small_dataset():
    txns = [
        {"id": i, "amount": -20.0, "date": date.today() - timedelta(days=i), "merchant_name": "Coffee Shop"}
        for i in range(8)
    ]
    txns.append({"id": 99, "amount": -900.0, "date": date.today(), "merchant_name": "Coffee Shop"})
    flagged = detect_anomalies(txns)
    assert any(f["id"] == 99 for f in flagged)


def test_anomaly_detection_too_few_transactions():
    txns = [{"id": 1, "amount": -20.0, "date": date.today(), "merchant_name": "Test"}]
    assert detect_anomalies(txns) == []
