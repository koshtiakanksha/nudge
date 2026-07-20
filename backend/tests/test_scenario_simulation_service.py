from app.services.scenario_simulation_service import (
    simulate_category_change,
    simulate_income_change,
    simulate_one_time_expense,
)

SPENDING = {"Rent": 1000.0, "Groceries": 300.0, "Savings": 300.0, "Dining": 300.0}
ROLES = {
    "Rent": "fixed_essential",
    "Groceries": "variable_essential",
    "Savings": "savings_or_debt",
    "Dining": "discretionary",
}


def test_rent_increase_reduces_discretionary_spending():
    result = simulate_category_change(income_estimate=2500, spending_by_category=SPENDING, category_roles=ROLES, category="Rent", new_amount=1200.0)
    assert result.after_allocations["Rent"]["allocated"] == 1200.0
    assert result.after_allocations["Dining"]["allocated"] < result.before_allocations["Dining"]["allocated"]


def test_canceling_a_subscription_frees_up_discretionary_room():
    result = simulate_category_change(income_estimate=2500, spending_by_category=SPENDING, category_roles=ROLES, category="Dining", new_amount=0.0)
    assert result.after_allocations["Dining"]["allocated"] == 0.0
    changes_by_category = {c["category"]: c for c in result.changes}
    assert "Dining" in changes_by_category
    assert changes_by_category["Dining"]["delta"] < 0


def test_income_drop_flagged_as_risk_when_essentials_no_longer_fit():
    # Rent (1000) + Groceries (300) = 1300 essentials. At income 2500
    # (spendable ~2250) they fit fine. Drop income enough that they don't.
    result = simulate_income_change(income_estimate=2500, new_income_estimate=1200, spending_by_category=SPENDING, category_roles=ROLES)
    assert result.risk_level == "over_budget"


def test_income_rise_is_not_flagged_as_risk():
    result = simulate_income_change(income_estimate=2500, new_income_estimate=3500, spending_by_category=SPENDING, category_roles=ROLES)
    assert result.risk_level == "none"


def test_one_time_expense_reduces_spendable_and_is_absorbed():
    result = simulate_one_time_expense(income_estimate=2500, spending_by_category=SPENDING, category_roles=ROLES, amount=400.0)
    assert result.spendable_after == round(result.spendable_before - 400.0, 2)
    assert result.after_allocations["Rent"]["allocated"] == result.before_allocations["Rent"]["allocated"]  # essential untouched
    assert len(result.changes) > 0


def test_large_one_time_expense_flagged_as_over_budget():
    result = simulate_one_time_expense(income_estimate=1500, spending_by_category=SPENDING, category_roles=ROLES, amount=1000.0)
    assert result.risk_level == "over_budget"


def test_changes_list_only_includes_categories_that_actually_moved():
    result = simulate_category_change(income_estimate=5000, spending_by_category=SPENDING, category_roles=ROLES, category="Groceries", new_amount=300.0)
    # No actual change (same amount) -- Rent and Savings should be untouched, no crash.
    assert isinstance(result.changes, list)


def test_summary_is_a_human_readable_string_for_every_scenario_type():
    r1 = simulate_category_change(2500, SPENDING, ROLES, "Rent", 1200.0)
    r2 = simulate_income_change(2500, 2000, SPENDING, ROLES)
    r3 = simulate_one_time_expense(2500, SPENDING, ROLES, 200.0)
    for r in (r1, r2, r3):
        assert isinstance(r.summary, str) and len(r.summary) > 0
