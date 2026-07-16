"""
Income intelligence service.

Fixes the bug where every positive transaction was summed as income
regardless of source (see the old summarize_transactions() in
statement_analysis_service.py, which did exactly that). Only
transactions that pass transaction_classification_service as
income-eligible -- i.e. not a transfer, refund, reimbursement, or fee
-- are ever grouped into income streams here.

Used identically by Plaid-synced transactions and parsed statement
uploads: both are lists of duck-typed objects with .amount,
.merchant_name, .raw_description, .date, and optionally .id.

Returns more than a single number, on purpose: a dollar figure alone
can't tell a user (or the budget engine) whether that number is safe
to plan around.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date as date_type
from datetime import timedelta

from app.services.transaction_classification_service import (
    classify_transaction,
    excluded_positive_transactions,
    merchant_key,
)

MIN_OCCURRENCES_FOR_STREAM = 2
AMOUNT_TOLERANCE_PCT = 0.15
AMOUNT_TOLERANCE_FLOOR = 10.0

FREQUENCY_MULTIPLIER = {
    "weekly": 4.33,
    "biweekly": 2.166,
    "semimonthly": 2.0,
    "monthly": 1.0,
    # "irregular" deliberately has no multiplier -- handled as a
    # special case in _build_streams via observed total / months spanned.
}


@dataclass
class IncomeStream:
    merchant_name: str
    average_amount: float
    frequency: str  # "weekly" | "biweekly" | "semimonthly" | "monthly" | "irregular"
    occurrences: int
    monthly_equivalent: float
    last_date: date_type
    next_expected_date: date_type | None
    confidence: float
    amount_cv: float = 0.0  # coefficient of variation *within* this stream's own amounts
    transaction_ids: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "merchant_name": self.merchant_name,
            "average_amount": round(self.average_amount, 2),
            "frequency": self.frequency,
            "occurrences": self.occurrences,
            "monthly_equivalent": round(self.monthly_equivalent, 2),
            "last_date": self.last_date,
            "next_expected_date": self.next_expected_date,
            "confidence": self.confidence,
            "transaction_ids": self.transaction_ids,
        }


@dataclass
class IncomeProfile:
    estimated_monthly_income: float
    conservative_monthly_income: float
    stability: str  # "stable" | "variable" | "insufficient_data"
    confidence: float
    streams: list  # list[IncomeStream]
    excluded_transactions: list  # list[dict] -- transfers/refunds/etc, with reasons
    unmatched_candidates: list  # list[dict] -- income-eligible but not recurring enough to be a stream
    months_of_history: int

    def to_dict(self) -> dict:
        return {
            "estimated_monthly_income": round(self.estimated_monthly_income, 2),
            "conservative_monthly_income": round(self.conservative_monthly_income, 2),
            "stability": self.stability,
            "confidence": self.confidence,
            "streams": [s.to_dict() for s in self.streams],
            "excluded_transactions": self.excluded_transactions,
            "unmatched_candidates": self.unmatched_candidates,
            "months_of_history": self.months_of_history,
        }


def _identity(t):
    key = getattr(t, "id", None)
    return key if key is not None else id(t)


def _frequency_for_delta(avg_delta_days: float) -> str:
    if 5 <= avg_delta_days <= 9:
        return "weekly"
    if 12 <= avg_delta_days <= 16:
        return "biweekly"
    if 16 < avg_delta_days <= 17:
        return "semimonthly"
    if 24 <= avg_delta_days <= 38:
        return "monthly"
    return "irregular"


def _build_streams(candidates: list) -> tuple[list[IncomeStream], set]:
    """Group income-eligible candidates into recurring streams.

    Returns (streams, used_identities) so the caller can tell which
    candidates never made it into a stream -- those are surfaced
    separately as unmatched_candidates rather than silently dropped.
    """
    grouped: dict[str, list] = defaultdict(list)
    for t in candidates:
        key = merchant_key(getattr(t, "merchant_name", None) or getattr(t, "raw_description", None))
        grouped[key].append(t)

    streams: list[IncomeStream] = []
    used_identities: set = set()

    for rows in grouped.values():
        if len(rows) < MIN_OCCURRENCES_FOR_STREAM:
            continue
        rows = sorted(rows, key=lambda t: t.date)
        amounts = [float(t.amount) for t in rows]
        avg_amount = statistics.mean(amounts)
        tolerance = max(avg_amount * AMOUNT_TOLERANCE_PCT, AMOUNT_TOLERANCE_FLOOR)
        if any(abs(a - avg_amount) > tolerance for a in amounts):
            # Too inconsistent in amount to trust as one stream. Left
            # unmatched rather than forced in.
            continue

        deltas = [(rows[i].date - rows[i - 1].date).days for i in range(1, len(rows))]
        avg_delta = statistics.mean(deltas) if deltas else 30
        frequency = _frequency_for_delta(avg_delta)

        median_amount = statistics.median(amounts)
        multiplier = FREQUENCY_MULTIPLIER.get(frequency)
        if multiplier is None:
            span_days = max((rows[-1].date - rows[0].date).days, 1)
            monthly_equivalent = sum(amounts) / (span_days / 30.44)
        else:
            monthly_equivalent = median_amount * multiplier

        confidence = 0.85 if frequency != "irregular" else 0.5
        if len(rows) >= 4:
            confidence = min(confidence + 0.1, 0.95)

        streams.append(IncomeStream(
            merchant_name=rows[-1].merchant_name or merchant_key(rows[-1].merchant_name),
            average_amount=avg_amount,
            frequency=frequency,
            occurrences=len(rows),
            monthly_equivalent=monthly_equivalent,
            last_date=rows[-1].date,
            next_expected_date=rows[-1].date + timedelta(days=round(avg_delta)) if avg_delta else None,
            confidence=confidence,
            amount_cv=_coefficient_of_variation(amounts) or 0.0,
            transaction_ids=[getattr(t, "id", None) for t in rows],
        ))
        used_identities.update(_identity(t) for t in rows)

    return sorted(streams, key=lambda s: s.monthly_equivalent, reverse=True), used_identities


def _coefficient_of_variation(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = statistics.mean(values)
    if mean == 0:
        return None
    return statistics.pstdev(values) / mean


def detect_income(transactions: list) -> IncomeProfile:
    """
    Main entry point.

    1. Classify every transaction; exclude transfers/refunds/
       reimbursements/fees before anything is grouped.
    2. Group the remaining income-eligible positive transactions into
       recurring streams by merchant + amount consistency + interval.
    3. Estimate monthly income two ways: a point estimate (sum of all
       stream monthly-equivalents) and a conservative one (discounts
       streams that aren't confidently recurring), because a budget
       engine should plan around the conservative number.
    """
    positive = [t for t in transactions if float(getattr(t, "amount", 0) or 0) > 0]
    candidates = [t for t in positive if classify_transaction(t).is_income_eligible]
    excluded = excluded_positive_transactions(transactions)

    dates = [t.date for t in transactions if getattr(t, "date", None)]
    months_of_history = len({(d.year, d.month) for d in dates}) if dates else 0

    streams, used_identities = _build_streams(candidates)
    unmatched_candidates = [
        {
            "transaction_id": getattr(t, "id", None),
            "merchant_name": getattr(t, "merchant_name", None),
            "amount": round(float(t.amount), 2),
            "date": t.date,
            "reason": "insufficient_occurrences_or_inconsistent_amount",
        }
        for t in candidates
        if _identity(t) not in used_identities
    ]

    if not streams:
        # No recurring pattern found. Fall back to a conservative
        # median-of-months estimate over income-eligible transactions
        # rather than reporting zero income outright.
        if candidates and months_of_history:
            monthly_totals: dict = defaultdict(float)
            for t in candidates:
                monthly_totals[(t.date.year, t.date.month)] += float(t.amount)
            totals = list(monthly_totals.values())
            estimated = statistics.median(totals)
            conservative = min(totals) if len(totals) > 1 else round(estimated * 0.85, 2)
            confidence = 0.35 if months_of_history >= 2 else 0.2
        else:
            estimated = conservative = 0.0
            confidence = 0.0
        return IncomeProfile(
            estimated_monthly_income=estimated,
            conservative_monthly_income=conservative,
            stability="insufficient_data",
            confidence=confidence,
            streams=[],
            excluded_transactions=excluded,
            unmatched_candidates=unmatched_candidates,
            months_of_history=months_of_history,
        )

    estimated_monthly_income = sum(s.monthly_equivalent for s in streams)
    conservative_monthly_income = sum(
        s.monthly_equivalent if s.confidence >= 0.8 else s.monthly_equivalent * 0.75
        for s in streams
    )

    # Stability reflects how consistent each stream's own amounts are
    # (amount_cv, computed when the stream was built), weighted by how
    # much of total income that stream represents. Deliberately NOT
    # bucketed by calendar month: a monthly payroll date can drift
    # across a month boundary (e.g. Jan 30 -> Mar 1 -> Mar 30), which
    # would put two payments in the same calendar bucket and one month
    # empty -- an artifact of the calendar, not real instability.
    if estimated_monthly_income > 0:
        weighted_cv = sum(
            s.amount_cv * s.monthly_equivalent for s in streams
        ) / estimated_monthly_income
        stability = "stable" if weighted_cv < 0.15 else "variable"
    else:
        stability = "insufficient_data"

    overall_confidence = round(statistics.mean([s.confidence for s in streams]), 2)

    return IncomeProfile(
        estimated_monthly_income=estimated_monthly_income,
        conservative_monthly_income=conservative_monthly_income,
        stability=stability,
        confidence=overall_confidence,
        streams=streams,
        excluded_transactions=excluded,
        unmatched_candidates=unmatched_candidates,
        months_of_history=months_of_history,
    )


def next_expected_deposits(profile: IncomeProfile) -> list[dict]:
    """Upcoming expected deposits across all streams, soonest first."""
    upcoming = [
        {
            "merchant_name": s.merchant_name,
            "expected_date": s.next_expected_date,
            "expected_amount": round(s.average_amount, 2),
        }
        for s in profile.streams
        if s.next_expected_date
    ]
    return sorted(upcoming, key=lambda d: d["expected_date"])


income_service = {
    "detect_income": detect_income,
    "next_expected_deposits": next_expected_deposits,
}
