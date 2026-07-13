"""
Synthetic budget request scenarios for evaluating app.services.claude_service
.generate_budget(). Varies income, spend ceiling, category mix, and
non-negotiables so the rubric isn't scored against one easy case.
"""
from __future__ import annotations

import numpy as np


def generate_budget_scenarios(seed: int = 42) -> list[dict]:
    rng = np.random.default_rng(seed)
    scenarios = []

    templates = [
        # (income, buffer_pct, categories, non_negotiables)
        (5200.0, 0.15, {"Rent": 1800, "Groceries": 500, "Dining": 300, "Transportation": 200,
                         "Entertainment": 150, "Utilities & Bills": 220}, ["Rent", "Utilities & Bills"]),
        (3100.0, 0.10, {"Rent": 1100, "Groceries": 320, "Dining": 180, "Transportation": 90,
                         "Subscriptions": 45}, ["Rent"]),
        (8800.0, 0.20, {"Rent": 2600, "Groceries": 700, "Dining": 650, "Travel": 500,
                         "Shopping": 400, "Health & Fitness": 180}, ["Rent"]),
        (2400.0, 0.05, {"Groceries": 260, "Dining": 90, "Transportation": 60,
                         "Subscriptions": 30}, []),
        (4600.0, 0.12, {"Rent": 1500, "Groceries": 450, "Dining": 260, "Transportation": 150,
                         "Health & Fitness": 90, "Entertainment": 110}, ["Rent", "Health & Fitness"]),
        # Edge case: empty spending history (new user, cold start)
        (5000.0, 0.15, {}, []),
        # Edge case: non-negotiable not present in historical spend
        (4000.0, 0.10, {"Groceries": 400, "Dining": 200}, ["Rent"]),
    ]

    for income, buffer_pct, categories, non_neg in templates:
        # Small perturbation so re-runs aren't byte-identical inputs.
        jittered = {k: round(v * rng.uniform(0.95, 1.05), 2) for k, v in categories.items()}
        scenarios.append(dict(
            monthly_income=income, spend_ceiling=None, buffer_pct=buffer_pct,
            spending_by_category=jittered, non_negotiables=non_neg,
        ))

    return scenarios
