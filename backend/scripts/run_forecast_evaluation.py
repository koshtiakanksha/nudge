"""
Runs the forecasting model benchmark across all synthetic household
profiles and writes a markdown report to backend/reports/forecast_benchmark.md.

Run with: python scripts/run_forecast_evaluation.py
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ml.evaluation.forecast_eval import run_full_benchmark  # noqa: E402


def main():
    report = run_full_benchmark(n_days=180, horizon=7, n_folds=6)
    summary = report.summary()
    detail = report.to_dataframe()

    out_dir = Path(__file__).resolve().parent.parent / "reports"
    out_dir.mkdir(exist_ok=True)

    lines = [
        "# Forecast Model Benchmark",
        "",
        f"Generated {datetime.now(timezone.utc).isoformat()} on synthetic household data. "
        "Lower WAPE/MAE/RMSE is better; coverage should sit near 0.8 for an 80% interval "
        "(too low = overconfident, too high = interval too wide to be useful).",
        "",
        "## Summary (mean across rolling-origin folds, all profiles)",
        "",
        summary.round(3).to_markdown(index=False),
        "",
        "## Winner by household profile (lowest WAPE)",
        "",
    ]
    for profile in summary["profile"].unique():
        sub = summary[summary["profile"] == profile].sort_values("wape")
        winner = sub.iloc[0]
        lines.append(f"- **{profile}**: {winner['model']} (WAPE {winner['wape']:.1f}%)")

    lines += ["", "## Per-fold detail", "", detail.round(3).to_markdown(index=False)]

    report_path = out_dir / "forecast_benchmark.md"
    report_path.write_text("\n".join(lines))
    print(f"Wrote {report_path}")
    print()
    print(summary.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
