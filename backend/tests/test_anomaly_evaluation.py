from app.ml.evaluation.anomaly_eval import _engineer_features, run_anomaly_benchmark, _score_run
from app.ml.evaluation.anomaly_models import ALL_DETECTORS, RuleBasedDetector
from app.ml.evaluation.synthetic_data import generate_labeled_transactions
import numpy as np


def test_feature_engineering_matches_production_columns():
    raw = generate_labeled_transactions("steady_earner", start_date="2025-01-01", n_days=60, seed=1)
    df = _engineer_features(raw)
    for col in ("amount_abs", "day_of_week", "merchant_avg", "deviation_from_merchant_avg"):
        assert col in df.columns


def test_score_run_perfect_detector_scores_max():
    raw = generate_labeled_transactions("steady_earner", start_date="2025-01-01", n_days=60, seed=1)
    df = _engineer_features(raw)
    perfect_flags = df["label"].isin(["unusual", "fraud"]).to_numpy()
    metrics = _score_run(df, perfect_flags)
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["false_alert_rate"] == 0.0


def test_score_run_flag_nothing_scores_zero_recall():
    raw = generate_labeled_transactions("steady_earner", start_date="2025-01-01", n_days=60, seed=1)
    df = _engineer_features(raw)
    metrics = _score_run(df, np.zeros(len(df), dtype=bool))
    assert metrics["recall"] == 0.0
    assert metrics["precision"] == 0.0


def test_rule_based_detector_runs_and_returns_bool_array():
    raw = generate_labeled_transactions("steady_earner", start_date="2025-01-01", n_days=60, seed=1)
    df = _engineer_features(raw)
    flagged, scores = RuleBasedDetector().fit_predict(df)
    assert flagged.dtype == bool
    assert len(flagged) == len(df)
    assert len(scores) == len(df)


def test_benchmark_runs_all_detectors_without_error():
    report = run_anomaly_benchmark("steady_earner", n_days=90, seeds=[1])
    df = report.to_dataframe()
    assert set(ALL_DETECTORS.keys()).issubset(set(df["model"]))
    assert (df["precision"] >= 0).all()
    assert (df["recall"] >= 0).all()
