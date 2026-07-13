"""
Runs the budget-recommendation evaluation rubric and writes a markdown
report to backend/reports/recommendation_benchmark.md.

Works in mock mode (no ANTHROPIC_API_KEY set) or against the real Claude
API — same code path either way. Run with:
    python scripts/run_recommendation_evaluation.py
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ml.evaluation.recommendation_eval import run_recommendation_benchmark  # noqa: E402


def main():
    report = run_recommendation_benchmark(n_consistency_runs=3)
    detail = report.to_dataframe()
    summary = report.summary()

    out_dir = Path(__file__).resolve().parent.parent / "reports"
    out_dir.mkdir(exist_ok=True)

    mode_note = (
        "Running in **mock mode** (no ANTHROPIC_API_KEY set) — grounding, budget-limit, and "
        "agreement checks are still real and meaningful against the rule-based fallback logic. "
        "Consistency reads 1.0 here by construction (the fallback is a deterministic function "
        "of its input); the interesting version of that number is what you get pointing this "
        "at the real API, where it isn't guaranteed. `est_cost_usd` is null because no request "
        "was actually billed."
        if report.mock_mode else
        "Running against the **real Claude API** — latency and estimated cost reflect actual calls."
    )

    lines = [
        "# Budget Recommendation Evaluation",
        "",
        f"Generated {datetime.now(timezone.utc).isoformat()}.",
        "",
        mode_note,
        "",
        "## Rubric",
        "",
        "- **category_grounding**: 1.0 = every allocated category was actually in the "
        "input (no invented categories)",
        "- **within_budget**: allocations don't exceed the computed spendable amount",
        "- **non_negotiables_covered**: fraction of required categories actually funded",
        "- **reasoning_cites_real_numbers**: does the prose explanation's numbers match "
        "the real buffer/spendable figures, or could it have said anything plausible-sounding?",
        "- **agreement_correlation**: Spearman correlation between historical category spend "
        "and allocated amount (do bigger historical categories get bigger budgets?)",
        "- **consistency**: same input run 3x — fraction of runs producing the same allocations",
        "",
        "## Summary (mean across all scenarios)",
        "",
        summary.round(3).to_markdown(index=False),
        "",
        "## Per-scenario detail",
        "",
        detail.round(3).to_markdown(index=False),
    ]

    report_path = out_dir / "recommendation_benchmark.md"
    report_path.write_text("\n".join(lines))
    print(f"Wrote {report_path}")
    print()
    print(summary.round(3).to_string(index=False))
    print()
    print(detail.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
