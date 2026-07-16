from datetime import date
from types import SimpleNamespace

from app.services.category_profile_service import (
    build_category_profile,
    build_category_profiles,
)


def _txn(amount, category, d, is_recurring=False, is_ignored=False, merchant="x"):
    return SimpleNamespace(
        amount=amount, nudge_category=category, date=d,
        is_recurring=is_recurring, is_ignored=is_ignored, merchant_name=merchant,
    )


def test_stable_groceries_gets_a_small_buffer():
    txns = [
        _txn(-291.0, "Groceries", date(2026, 1, 15)),
        _txn(-284.0, "Groceries", date(2026, 2, 15)),
        _txn(-296.0, "Groceries", date(2026, 3, 15)),
    ]
    profile = build_category_profile("Groceries", txns)
    assert profile.role == "variable_essential"
    assert profile.buffer_pct < 0.10
    assert 250 < profile.suggested_amount < 340


def test_volatile_travel_gets_a_bigger_buffer_than_stable_groceries():
    groceries = [
        _txn(-291.0, "Groceries", date(2026, 1, 15)),
        _txn(-284.0, "Groceries", date(2026, 2, 15)),
        _txn(-296.0, "Groceries", date(2026, 3, 15)),
    ]
    travel = [
        _txn(-50.0, "Travel", date(2026, 1, 15)),
        _txn(-620.0, "Travel", date(2026, 2, 15)),
        _txn(-40.0, "Travel", date(2026, 3, 15)),
    ]
    groceries_profile = build_category_profile("Groceries", groceries)
    travel_profile = build_category_profile("Travel", travel)
    assert travel_profile.volatility > groceries_profile.volatility
    assert travel_profile.buffer_pct > groceries_profile.buffer_pct


def test_rent_with_recurring_flag_uses_recurring_amount_directly():
    txns = [
        _txn(-1800.0, "Rent", date(2026, 1, 1), is_recurring=True),
        _txn(-1800.0, "Rent", date(2026, 2, 1), is_recurring=True),
        _txn(-1800.0, "Rent", date(2026, 3, 1), is_recurring=True),
    ]
    profile = build_category_profile("Rent", txns)
    assert profile.role == "fixed_essential"
    assert profile.suggested_amount == 1800.0
    assert profile.used_recurring_amount is True


def test_baseline_path_does_not_claim_recurring_amount():
    txns = [
        _txn(-291.0, "Groceries", date(2026, 1, 15)),
        _txn(-284.0, "Groceries", date(2026, 2, 15)),
        _txn(-296.0, "Groceries", date(2026, 3, 15)),
    ]
    profile = build_category_profile("Groceries", txns)
    assert profile.used_recurring_amount is False


def test_category_type_override_changes_role_and_therefore_buffer():
    # "Dining" defaults to discretionary; a user marking it fixed
    # (e.g. a meal plan) should change both role and buffer treatment.
    txns = [
        _txn(-400.0, "Dining", date(2026, 1, 1)),
        _txn(-400.0, "Dining", date(2026, 2, 1)),
    ]
    default_profile = build_category_profile("Dining", txns)
    override_profile = build_category_profile("Dining", txns, category_type="fixed")
    assert default_profile.role == "discretionary"
    assert override_profile.role == "fixed_essential"
    assert override_profile.buffer_pct < default_profile.buffer_pct


def test_increasing_trend_detected():
    txns = [
        _txn(-100.0, "Shopping", date(2026, 1, 1)),
        _txn(-110.0, "Shopping", date(2026, 2, 1)),
        _txn(-250.0, "Shopping", date(2026, 3, 1)),
        _txn(-260.0, "Shopping", date(2026, 4, 1)),
    ]
    profile = build_category_profile("Shopping", txns)
    assert profile.trend == "increasing"


def test_decreasing_trend_detected():
    txns = [
        _txn(-260.0, "Shopping", date(2026, 1, 1)),
        _txn(-250.0, "Shopping", date(2026, 2, 1)),
        _txn(-110.0, "Shopping", date(2026, 3, 1)),
        _txn(-100.0, "Shopping", date(2026, 4, 1)),
    ]
    profile = build_category_profile("Shopping", txns)
    assert profile.trend == "decreasing"


def test_savings_role_has_zero_buffer():
    txns = [
        _txn(-500.0, "Savings", date(2026, 1, 1)),
        _txn(-500.0, "Savings", date(2026, 2, 1)),
    ]
    profile = build_category_profile("Savings", txns)
    assert profile.role == "savings_or_debt"
    assert profile.buffer_pct == 0.0


def test_empty_transaction_list_does_not_error():
    profile = build_category_profile("Pottery Classes", [])
    assert profile.role == "unclassified"
    assert profile.suggested_amount == 0.0
    assert profile.trend == "insufficient_data"


def test_build_category_profiles_groups_and_skips_income_and_ignored():
    txns = [
        _txn(-291.0, "Groceries", date(2026, 1, 1)),
        _txn(-284.0, "Groceries", date(2026, 2, 1)),
        _txn(1986.42, "Income", date(2026, 1, 30)),  # positive -- not an expense
        _txn(-50.0, "Dining", date(2026, 1, 5), is_ignored=True),  # ignored
        _txn(-60.0, "Dining", date(2026, 2, 5)),
    ]
    profiles = build_category_profiles(txns)
    assert set(profiles.keys()) == {"Groceries", "Dining"}
    assert profiles["Dining"].transaction_count == 1  # the ignored one excluded


def test_confidence_increases_with_more_history():
    short = [_txn(-100.0, "Dining", date(2026, 1, 1))]
    longer = [
        _txn(-100.0, "Dining", date(2026, 1, 1)),
        _txn(-100.0, "Dining", date(2026, 2, 1)),
        _txn(-100.0, "Dining", date(2026, 3, 1)),
        _txn(-100.0, "Dining", date(2026, 4, 1)),
    ]
    short_profile = build_category_profile("Dining", short)
    longer_profile = build_category_profile("Dining", longer)
    assert longer_profile.confidence > short_profile.confidence
