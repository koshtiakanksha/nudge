"""
Evaluation rubric for app.services.claude_service.generate_budget().

There's no ground-truth "correct budget" the way there's a ground-truth
forecast value, so this doesn't score against a label. It scores four
things that are checkable regardless of whether the underlying model is
the mock rule-based fallback or the real Claude API:

1. Factual grounding — does the output only reference categories that were
   actually given to it, stay within the spendable amount, and does its
   prose reasoning cite numbers that match what was actually computed
   (not just plausible-sounding numbers)?
2. Agreement with transaction data — do categories with more historical
   spend get more budget, directionally?
3. Consistency — same input, same output? (Mock mode is deterministic by
   construction, so this will read 1.0 there; the same harness run against
   the real API is what would actually be interesting, and is designed
   to just work if ANTHROPIC_API_KEY is set — see run_recommendation_evaluation.py.)
4. Cost and latency — wall-clock time per call, and estimated per-call
   cost when running against the real API (token counts are known from
   the prompt template; mock mode is $0 by construction).
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

import numpy as np

from app.ml.evaluation.recommendation_scenarios import generate_budget_scenarios
from app.services.claude_service import claude_service

# Approximate per-request pricing for the configured model, used only to
# estimate cost when the real API is in use. Update if claude_model changes.
_PRICE_PER_1K_INPUT = 0.003
_PRICE_PER_1K_OUTPUT = 0.015
_APPROX_CHARS_PER_TOKEN = 4


@dataclass
class ScenarioResult:
    scenario_idx: int
    category_grounding: float       # 1.0 = no hallucinated categories
    within_budget: bool
    non_negotiables_covered: float  # fraction of non-negotiables present & funded
    reasoning_cites_real_numbers: float  # 0/0.5/1: neither/one-of/both buffer+spendable match
    agreement_correlation: float | None   # Spearman corr, historical share vs allocated share
    consistency: float              # fraction of repeated runs producing identical allocations
    latency_seconds: float
    est_cost_usd: float | None      # None in mock mode (no real request made)


@dataclass
class RecommendationReport:
    results: list[ScenarioResult] = field(default_factory=list)
    mock_mode: bool = True

    def to_dataframe(self):
        import pandas as pd
        return pd.DataFrame([r.__dict__ for r in self.results])

    def summary(self):
        import pandas as pd
        df = self.to_dataframe()
        if df.empty:
            return df
        agg = {
            "category_grounding": "mean", "within_budget": "mean",
            "non_negotiables_covered": "mean", "reasoning_cites_real_numbers": "mean",
            "agreement_correlation": "mean", "consistency": "mean",
            "latency_seconds": "mean",
        }
        if df["est_cost_usd"].notna().any():
            agg["est_cost_usd"] = "mean"
        return pd.DataFrame([df.agg(agg)])


def _extract_numbers(text: str) -> list[float]:
    return [float(m.replace(",", "")) for m in re.findall(r"\d[\d,]*\.?\d*", text or "")]


def _spearman(a: list[float], b: list[float]) -> float | None:
    if len(a) < 2:
        return None
    ra = pd_rank(a)
    rb = pd_rank(b)
    if np.std(ra) == 0 or np.std(rb) == 0:
        return None
    return float(np.corrcoef(ra, rb)[0, 1])


def pd_rank(values: list[float]) -> np.ndarray:
    order = np.argsort(np.argsort(values))
    return order.astype(float)


def _score_grounding(result: dict, spendable: float, buffer_reserved: float,
                      spending_by_category: dict, non_negotiables: list[str]) -> dict:
    allocations = result.get("allocations", {})
    allowed = set(spending_by_category.keys()) | set(non_negotiables)

    if not allocations:
        category_grounding = 0.0
    else:
        hallucinated = [c for c in allocations if allowed and c not in allowed]
        category_grounding = 1.0 - (len(hallucinated) / len(allocations)) if allowed else 1.0

    total_allocated = sum(a.get("allocated", 0) for a in allocations.values())
    within_budget = total_allocated <= spendable * 1.01 + 0.01

    if non_negotiables:
        covered = sum(
            1 for c in non_negotiables
            if c in allocations and allocations[c].get("is_non_neg") and allocations[c].get("allocated", 0) > 0
        )
        non_neg_covered = covered / len(non_negotiables)
    else:
        non_neg_covered = 1.0

    reasoning_numbers = _extract_numbers(result.get("reasoning", ""))
    mentions_buffer = any(abs(n - buffer_reserved) < 1.0 for n in reasoning_numbers)
    mentions_spendable = any(abs(n - spendable) < 1.0 for n in reasoning_numbers)
    reasoning_score = (int(mentions_buffer) + int(mentions_spendable)) / 2

    return dict(
        category_grounding=category_grounding, within_budget=within_budget,
        non_negotiables_covered=non_neg_covered, reasoning_cites_real_numbers=reasoning_score,
    )


def _score_agreement(result: dict, spending_by_category: dict) -> float | None:
    allocations = result.get("allocations", {})
    shared = [c for c in spending_by_category if c in allocations]
    if len(shared) < 2:
        return None
    historical = [spending_by_category[c] for c in shared]
    allocated = [allocations[c].get("allocated", 0) for c in shared]
    return _spearman(historical, allocated)


def _score_consistency(scenario: dict, n_runs: int = 3) -> float:
    outputs = [claude_service.generate_budget(**scenario) for _ in range(n_runs)]
    baseline = outputs[0].get("allocations", {})

    def _same(a: dict, b: dict) -> bool:
        if set(a.keys()) != set(b.keys()):
            return False
        return all(abs(a[k].get("allocated", 0) - b[k].get("allocated", 0)) < 0.5 for k in a)

    matches = sum(1 for o in outputs if _same(o.get("allocations", {}), baseline))
    return matches / n_runs


def _estimate_cost(prompt_chars: int, response_chars: int) -> float:
    input_tokens = prompt_chars / _APPROX_CHARS_PER_TOKEN
    output_tokens = response_chars / _APPROX_CHARS_PER_TOKEN
    return (input_tokens / 1000) * _PRICE_PER_1K_INPUT + (output_tokens / 1000) * _PRICE_PER_1K_OUTPUT


def run_recommendation_benchmark(n_consistency_runs: int = 3, seed: int = 42) -> RecommendationReport:
    scenarios = generate_budget_scenarios(seed=seed)
    mock_mode = claude_service.mock_mode
    report = RecommendationReport(mock_mode=mock_mode)

    for i, scenario in enumerate(scenarios):
        spend_ceiling = scenario["spend_ceiling"] or (
            scenario["monthly_income"] * (1 - scenario["buffer_pct"])
        )
        buffer_reserved = round(scenario["monthly_income"] * scenario["buffer_pct"], 2)
        spendable = round(spend_ceiling - buffer_reserved, 2)

        start = time.perf_counter()
        result = claude_service.generate_budget(**scenario)
        latency = time.perf_counter() - start

        grounding = _score_grounding(
            result, spendable, buffer_reserved,
            scenario["spending_by_category"], scenario["non_negotiables"],
        )
        agreement = _score_agreement(result, scenario["spending_by_category"])
        consistency = _score_consistency(scenario, n_runs=n_consistency_runs)

        est_cost = None
        if not mock_mode:
            reasoning_text = result.get("reasoning", "")
            est_cost = _estimate_cost(prompt_chars=1200, response_chars=len(reasoning_text) + 400)

        report.results.append(ScenarioResult(
            scenario_idx=i,
            category_grounding=grounding["category_grounding"],
            within_budget=grounding["within_budget"],
            non_negotiables_covered=grounding["non_negotiables_covered"],
            reasoning_cites_real_numbers=grounding["reasoning_cites_real_numbers"],
            agreement_correlation=agreement,
            consistency=consistency,
            latency_seconds=latency,
            est_cost_usd=est_cost,
        ))

    return report
