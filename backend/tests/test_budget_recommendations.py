"""
Tests for statement_analysis_service.budget_recommendations().

budget_recommendations() itself never calls claude_service, but the
module imports it at load time. That's fine here: ClaudeService falls
back to mock_mode (no LLM call) whenever no ANTHROPIC_API_KEY is
configured, so no stubbing is needed -- anthropic/pydantic-settings are
already real project dependencies.
"""
from datetime import date, timedelta
from types import SimpleNamespace

from app.services.statement_analysis_service import budget_recommendations


def _txn(amount, merchant="", desc="", d=date(2026, 1, 1), cat=None, id_=None, is_recurring=False):
    return SimpleNamespace(
        id=id_, amount=amount, merchant_name=merchant, raw_description=desc,
        date=d, nudge_category=cat, is_ignored=False, is_anomaly=False, is_recurring=is_recurring,
    )


def _payroll(months=3, amount=1986.42):
    return [
        _txn(amount, "ISU PAYROLL", "payroll deposit", date(2026, 1, 30) + timedelta(days=30 * i), id_=f"pay{i}")
        for i in range(months)
    ]


def _rent(amount=900.0):
    return [
        _txn(-amount, "Landlord LLC", "rent", d, cat="Rent", id_=f"rent{i}", is_recurring=True)
        for i, d in enumerate([date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)])
    ]


def _savings(amount=200.0):
    return [
        _txn(-amount, "Vanguard", "savings", d, cat="Savings", id_=f"sav{i}")
        for i, d in enumerate([date(2026, 1, 20), date(2026, 2, 20), date(2026, 3, 20)])
    ]


def _dining(amount=350.0):
    return [
        _txn(-amount, "Restaurant", "dining", d, cat="Dining", id_=f"din{i}")
        for i, d in enumerate([date(2026, 1, 25), date(2026, 2, 25), date(2026, 3, 25)])
    ]


def test_no_duplicate_savings_category_when_real_savings_history_exists():
    txns = _payroll() + _rent() + _savings() + _dining()
    result = budget_recommendations(txns, date(2026, 4, 1))
    categories = [r["category"] for r in result["recommendations"]]
    assert categories.count("Savings") == 1


def test_savings_funded_meaningfully_not_left_at_zero():
    txns = _payroll() + _rent() + _savings() + _dining()
    result = budget_recommendations(txns, date(2026, 4, 1))
    savings_rec = next(r for r in result["recommendations"] if r["category"] == "Savings")
    assert savings_rec["recommended_amount"] == 200.0


def test_no_synthetic_savings_row_when_no_real_savings_and_no_leftover():
    txns = _payroll() + _rent() + _dining()
    result = budget_recommendations(txns, date(2026, 4, 1))
    categories = [r["category"] for r in result["recommendations"]]
    assert "Savings" not in categories  # nothing to fabricate a $0 row for


def test_unallocated_leftover_labeled_distinctly_when_savings_already_used():
    # Rent + Savings only, no discretionary category to stretch and
    # consume the remainder -- a real leftover exists on top of an
    # already-present Savings recommendation.
    txns = _payroll(amount=3000.0) + _rent() + _savings()
    result = budget_recommendations(txns, date(2026, 4, 1))
    categories = [r["category"] for r in result["recommendations"]]
    assert categories.count("Savings") == 1
    assert "Unallocated" in categories


def test_allocations_never_exceed_spendable_income():
    txns = _payroll() + _rent(1800.0) + [
        _txn(-600.0, "Whole Foods", "groceries", d, cat="Groceries", id_=f"g{i}")
        for i, d in enumerate([date(2026, 1, 15), date(2026, 2, 15), date(2026, 3, 15)])
    ]
    result = budget_recommendations(txns, date(2026, 4, 1))
    non_savings_total = sum(
        r["recommended_amount"] for r in result["recommendations"]
        if r["category"] not in {"Savings", "Unallocated"}
    )
    assert non_savings_total <= result["allocation"]["spendable"] + 0.01


def test_engine_version_is_v2():
    txns = _payroll() + _rent() + _dining()
    result = budget_recommendations(txns, date(2026, 4, 1))
    assert result["allocation"]["engine_version"] == "budget-engine-v2"
