"""
Runs the anomaly detection benchmark across all synthetic household
profiles and writes a markdown report to backend/reports/anomaly_benchmark.md.

Run with: python scripts/run_anomaly_evaluation.py
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ml.evaluation.anomaly_eval import run_full_anomaly_benchmark  # noqa: E402


def main():
    report = run_full_anomaly_benchmark(n_days=120, seeds=[1, 2, 3, 4, 5])
    summary = report.summary()
    detail = report.to_dataframe()

    out_dir = Path(__file__).resolve().parent.parent / "reports"
    out_dir.mkdir(exist_ok=True)

    lines = [
        "# Anomaly Detection Benchmark",
        "",
        f"Generated {datetime.now(timezone.utc).isoformat()} on synthetic labeled transactions "
        "(labels: normal / unusual / fraud, unknown to every detector under test). "
        "'unusual' and 'fraud' are both scored as the positive (anomalous) class for "
        "precision/recall/F1, since that's what production currently outputs — a single "
        "flag with no severity split. `pct_fraud_caught` shows recall computed on the "
        "fraud subset alone.",
        "",
        "## Summary (mean across 5 seeds, all profiles)",
        "",
        summary.round(3).to_markdown(index=False),
        "",
        "## Winner by household profile (highest F1)",
        "",
    ]
    for profile in summary["profile"].unique():
        sub = summary[summary["profile"] == profile].sort_values("f1", ascending=False)
        winner = sub.iloc[0]
        lines.append(
            f"- **{profile}**: {winner['model']} "
            f"(F1 {winner['f1']:.2f}, false-alert rate {winner['false_alert_rate']:.3f})"
        )

    lines += [
        "",
        "## Known gap this benchmark surfaces",
        "",
        "No detector here — including production's Isolation Forest — has features that "
        "distinguish 'unusual' from 'fraud' specifically (merchant familiarity, geographic "
        "distance from typical spend, account-age-at-merchant). `pct_fraud_caught` in the "
        "detail table shows fraud is being caught largely as a side effect of being a big, "
        "unfamiliar-merchant outlier, not because any model is reasoning about fraud "
        "specifically. Next step if pursued: add merchant-familiarity and geo features and "
        "score fraud recall as its own metric, not a subset of general anomaly recall.",
        "",
        "## Per-run detail",
        "",
        detail.round(3).to_markdown(index=False),
    ]

    report_path = out_dir / "anomaly_benchmark.md"
    report_path.write_text("\n".join(lines))
    print(f"Wrote {report_path}")
    print()
    print(summary.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
