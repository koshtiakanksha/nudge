from app.ml.evaluation.forecast_eval import run_forecast_benchmark
from app.ml.evaluation.synthetic_data import generate_daily_spend, generate_labeled_transactions


def test_generate_daily_spend_shape():
    df = generate_daily_spend("steady_earner", start_date="2025-01-01", n_days=60)
    assert len(df) == 60
    assert (df["amount"] >= 0).all()


def test_generate_labeled_transactions_has_all_labels():
    df = generate_labeled_transactions("steady_earner", start_date="2025-01-01", n_days=120, seed=1)
    labels = set(df["label"].unique())
    assert "normal" in labels
    # With 120 days at ~3 txns/day and a 3.5% combined anomaly+fraud rate,
    # we expect to see both rarer classes represented.
    assert "unusual" in labels
    assert "fraud" in labels


def test_benchmark_runs_without_prophet_or_error():
    # include_prophet=True by default; if prophet isn't installed this
    # should degrade to a "prophet_UNAVAILABLE" row, not raise.
    report = run_forecast_benchmark(
        profile="steady_earner", n_days=90, horizon=7, n_folds=3, include_models=["seasonal_naive"],
    )
    df = report.to_dataframe()
    assert not df.empty
    assert "seasonal_naive" in df["model"].values


def test_benchmark_summary_ranks_models():
    report = run_forecast_benchmark(
        profile="steady_earner", n_days=90, horizon=7, n_folds=3,
        include_models=["seasonal_naive", "moving_average"], include_prophet=False,
    )
    summary = report.summary()
    assert set(summary["model"]) == {"seasonal_naive", "moving_average"}
    # WAPE should be non-negative for every model that ran successfully.
    assert (summary["wape"] >= 0).all()
