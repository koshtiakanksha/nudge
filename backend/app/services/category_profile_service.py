"""
Category spending profile service.

Replaces the flat "total spend / months, with a hardcoded 10% haircut
on Dining/Shopping/Entertainment only" logic that used to live directly
in statement_analysis_service.budget_recommendations. That formula
treated every category the same and was distorted by any single
expensive month. This module computes, per category:

    median monthly spend, a recency-weighted average, a recurring
    component, MAD-based (outlier-resistant) volatility, a typical
    range, a trend, a role-aware buffer, and a suggested amount.

Known limitation: category_types (BudgetCategory.category_type
overrides from the DB) aren't wired in yet -- build_category_profiles()
only sees transactions, not a user_id/db session, so role inference
falls back to name-based defaults from category_role_service for every
caller today. Per-user overrides arrive when the two budget flows get
consolidated into one pipeline with real DB access (a later step).

Also: "recurring_component" depends on transactions having
is_recurring set. Statement-uploaded transactions (ParsedTransaction)
don't carry that flag at all -- only Plaid-synced ORM Transactions can.
So today, this mostly falls back to baseline-plus-buffer even for rent
when called from the statement-upload path; it's a real result, just
not the sharper "forecast rent from its recurring amount" version yet.

Savings/debt categories get a 0% buffer since baseline-plus-buffer
doesn't really apply to a goal-driven category -- but there's no actual
goal/target modeling in this codebase yet, so the "suggested_amount"
for savings_or_debt right now is still just historical baseline, not a
real goal. Flagging honestly rather than pretending it's goal-aware.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass

from app.services.category_role_service import (
    ROLE_DISCRETIONARY,
    ROLE_FIXED_ESSENTIAL,
    ROLE_SAVINGS_OR_DEBT,
    ROLE_UNCLASSIFIED,
    ROLE_VARIABLE_ESSENTIAL,
    infer_role,
)

MIN_BUFFER = 0.02
MAX_BUFFER = 0.20
ROLE_BASE_BUFFER = {
    ROLE_FIXED_ESSENTIAL: 0.02,
    ROLE_VARIABLE_ESSENTIAL: 0.05,
    ROLE_DISCRETIONARY: 0.08,
    ROLE_SAVINGS_OR_DEBT: 0.0,
    ROLE_UNCLASSIFIED: 0.06,
}
RECENCY_DECAY = 0.7  # each month further back is weighted 0.7x the one after it


@dataclass
class CategoryProfile:
    category: str
    role: str
    months_of_history: int
    transaction_count: int
    median_monthly_spend: float
    weighted_recent_average: float
    recurring_component: float
    volatility: float  # robust coefficient of variation (MAD-based); 0 = perfectly steady
    typical_range: tuple
    trend: str  # "increasing" | "decreasing" | "flat" | "insufficient_data"
    buffer_pct: float
    suggested_amount: float
    confidence: float
    used_recurring_amount: bool = False

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "role": self.role,
            "months_of_history": self.months_of_history,
            "transaction_count": self.transaction_count,
            "median_monthly_spend": round(self.median_monthly_spend, 2),
            "weighted_recent_average": round(self.weighted_recent_average, 2),
            "recurring_component": round(self.recurring_component, 2),
            "volatility": round(self.volatility, 3),
            "typical_range": [round(self.typical_range[0], 2), round(self.typical_range[1], 2)],
            "trend": self.trend,
            "buffer_pct": round(self.buffer_pct, 3),
            "suggested_amount": round(self.suggested_amount, 2),
            "confidence": self.confidence,
            "used_recurring_amount": self.used_recurring_amount,
        }


def _median_absolute_deviation(values: list[float]) -> float:
    med = statistics.median(values)
    return statistics.median([abs(v - med) for v in values])


def _robust_cv(values: list[float]) -> float:
    """Coefficient-of-variation-like measure built from MAD instead of
    stdev. MAD is far less distorted by a single expensive month than
    stdev is, and stays meaningful with only a few data points -- both
    matter here since most categories will have 2-6 months of history,
    not enough for stdev to be trustworthy."""
    if len(values) < 2:
        return 0.0
    med = statistics.median(values)
    if med == 0:
        return 0.0
    mad = _median_absolute_deviation(values)
    # 1.4826 is the standard constant that scales MAD to be comparable
    # to a standard deviation under a normal distribution.
    return (mad * 1.4826) / med


def _monthly_totals(transactions: list) -> dict:
    totals: dict = defaultdict(float)
    for t in transactions:
        totals[(t.date.year, t.date.month)] += abs(float(t.amount))
    return totals


def _weighted_recent_average(monthly_values_newest_first: list[float]) -> float:
    weights = [RECENCY_DECAY**i for i in range(len(monthly_values_newest_first))]
    total_weight = sum(weights)
    return sum(v * w for v, w in zip(monthly_values_newest_first, weights)) / total_weight


def _trend_for(monthly_values_oldest_first: list[float]) -> str:
    if len(monthly_values_oldest_first) < 2:
        return "insufficient_data"
    mid = len(monthly_values_oldest_first) // 2
    first_half = monthly_values_oldest_first[:mid] or monthly_values_oldest_first[:1]
    second_half = monthly_values_oldest_first[mid:]
    early = statistics.mean(first_half)
    late = statistics.mean(second_half)
    if early == 0:
        return "insufficient_data"
    change = (late - early) / early
    if change > 0.10:
        return "increasing"
    if change < -0.10:
        return "decreasing"
    return "flat"


def _confidence_for(months_of_history: int, transaction_count: int) -> float:
    base = min(months_of_history / 4, 1.0) * 0.6 + min(transaction_count / 8, 1.0) * 0.4
    return round(max(base, 0.1), 2)


def build_category_profile(category: str, transactions: list, category_type: str | None = None) -> CategoryProfile:
    """
    Build a profile for one category's expense transactions.

    transactions is expected to already be filtered to this category's
    expense rows -- same convention statement_analysis_service.category_totals()
    uses (the caller does the filtering, this just computes statistics).
    """
    role = infer_role(category, category_type)
    monthly_totals = _monthly_totals(transactions)
    months_desc = sorted(monthly_totals.keys(), reverse=True)
    values_newest_first = [monthly_totals[m] for m in months_desc]
    values_oldest_first = list(reversed(values_newest_first))

    months_of_history = len(monthly_totals)
    transaction_count = len(transactions)

    if not values_newest_first:
        median_monthly_spend = weighted_recent_average = 0.0
        volatility = 0.0
        typical_range = (0.0, 0.0)
        trend = "insufficient_data"
    else:
        median_monthly_spend = statistics.median(values_newest_first)
        weighted_recent_average = _weighted_recent_average(values_newest_first)
        volatility = _robust_cv(values_newest_first)
        if len(values_newest_first) >= 2:
            mad = _median_absolute_deviation(values_newest_first)
            typical_range = (max(median_monthly_spend - mad, 0), median_monthly_spend + mad)
        else:
            typical_range = (values_newest_first[0], values_newest_first[0])
        trend = _trend_for(values_oldest_first)

    recurring_amounts = [abs(float(t.amount)) for t in transactions if getattr(t, "is_recurring", False)]
    recurring_component = statistics.median(recurring_amounts) if recurring_amounts else 0.0

    buffer_pct = ROLE_BASE_BUFFER.get(role, ROLE_BASE_BUFFER[ROLE_UNCLASSIFIED])
    if role != ROLE_SAVINGS_OR_DEBT:
        buffer_pct = min(max(buffer_pct + min(volatility, 0.3) * 0.4, MIN_BUFFER), MAX_BUFFER)

    if role == ROLE_FIXED_ESSENTIAL and recurring_component > 0:
        # A confirmed recurring amount is a stronger signal than a
        # volatility buffer for something like rent -- use it directly.
        suggested_amount = recurring_component
        used_recurring_amount = True
    else:
        baseline = (
            0.5 * weighted_recent_average
            + 0.3 * median_monthly_spend
            + 0.2 * (recurring_component or weighted_recent_average)
        )
        suggested_amount = baseline if role == ROLE_SAVINGS_OR_DEBT else baseline * (1 + buffer_pct)
        used_recurring_amount = False

    return CategoryProfile(
        category=category,
        role=role,
        months_of_history=months_of_history,
        transaction_count=transaction_count,
        median_monthly_spend=median_monthly_spend,
        weighted_recent_average=weighted_recent_average,
        recurring_component=recurring_component,
        volatility=volatility,
        typical_range=typical_range,
        trend=trend,
        buffer_pct=buffer_pct,
        suggested_amount=suggested_amount,
        confidence=_confidence_for(months_of_history, transaction_count),
        used_recurring_amount=used_recurring_amount,
    )


def build_category_profiles(transactions: list, category_types: dict | None = None) -> dict:
    """Group expense transactions by category (same convention as
    category_totals: skips ignored and non-expense rows) and build a
    profile per category. category_types maps category name ->
    BudgetCategory.category_type, when the caller has it."""
    category_types = category_types or {}
    by_category: dict = defaultdict(list)
    for t in transactions:
        if getattr(t, "is_ignored", False) or float(t.amount) >= 0:
            continue
        cat = t.nudge_category or "Other"
        by_category[cat].append(t)

    return {
        cat: build_category_profile(cat, rows, category_types.get(cat))
        for cat, rows in by_category.items()
    }


category_profile_service = {
    "build_category_profile": build_category_profile,
    "build_category_profiles": build_category_profiles,
}
