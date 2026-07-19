from app.services.budget_engine import compute_budget_allocation, compute_budget_allocation_v2


def test_fixed_essential_funded_first_and_scaled_down_when_it_exceeds_spendable():
    result = compute_budget_allocation_v2(
        spendable=1500.0,
        buffer_reserved=200.0,
        spending_by_category={"Rent": 1800.0},
        category_roles={"Rent": "fixed_essential"},
    )
    assert result.non_negotiables_constrained is True
    assert result.allocations["Rent"]["allocated"] == 1500.0
    assert result.allocations["Rent"]["is_non_neg"] is True


def test_savings_is_funded_before_discretionary_unlike_v1():
    # The core fix: Savings and Dining have similar historical weight,
    # but Savings should get funded to its own baseline BEFORE Dining
    # gets anything -- v1 would split the remainder between them
    # proportionally instead, which could starve Savings if Dining's
    # historical total happened to be larger.
    spending = {"Rent": 1000.0, "Savings": 300.0, "Dining": 400.0}
    roles = {"Rent": "fixed_essential", "Savings": "savings_or_debt", "Dining": "discretionary"}

    v1 = compute_budget_allocation(spendable=1400.0, buffer_reserved=100.0, spending_by_category=spending, non_negotiables=["Rent"])
    v2 = compute_budget_allocation_v2(spendable=1400.0, buffer_reserved=100.0, spending_by_category=spending, category_roles=roles)

    # v1: remaining 400 split proportionally between Savings (300) and
    # Dining (400) by weight -> Savings gets less than its own $300 ask.
    assert v1.allocations["Savings"]["allocated"] < 300.0

    # v2: Savings gets funded to its full $300 ask first; Dining gets
    # whatever's left (100).
    assert v2.allocations["Savings"]["allocated"] == 300.0
    assert v2.allocations["Dining"]["allocated"] == 100.0


def test_variable_essential_is_capped_to_its_own_baseline_not_stretched():
    # Groceries (variable_essential) shouldn't get inflated beyond its
    # own $300 baseline just because there's room left in the budget --
    # that room should flow to savings/discretionary instead.
    spending = {"Rent": 1000.0, "Groceries": 300.0, "Savings": 500.0}
    roles = {"Rent": "fixed_essential", "Groceries": "variable_essential", "Savings": "savings_or_debt"}
    result = compute_budget_allocation_v2(spendable=2000.0, buffer_reserved=0.0, spending_by_category=spending, category_roles=roles)
    assert result.allocations["Groceries"]["allocated"] == 300.0
    assert result.allocations["Savings"]["allocated"] == 500.0


def test_essential_tiers_scaled_down_together_when_tier_total_exceeds_remaining():
    spending = {"Rent": 1000.0, "Groceries": 400.0, "Utilities": 200.0}
    roles = {"Rent": "fixed_essential", "Groceries": "variable_essential", "Utilities": "variable_essential"}
    # After Rent (1000), only 300 remains for a 600-total variable_essential tier.
    result = compute_budget_allocation_v2(spendable=1300.0, buffer_reserved=0.0, spending_by_category=spending, category_roles=roles)
    assert result.allocations["Rent"]["allocated"] == 1000.0
    # 300 remaining split proportionally across the 400/200 tier -> 200 and 100
    assert result.allocations["Groceries"]["allocated"] == 200.0
    assert result.allocations["Utilities"]["allocated"] == 100.0


def test_discretionary_gets_whatever_is_left_proportionally():
    spending = {"Rent": 800.0, "Dining": 300.0, "Shopping": 100.0}
    roles = {"Rent": "fixed_essential", "Dining": "discretionary", "Shopping": "discretionary"}
    result = compute_budget_allocation_v2(spendable=1200.0, buffer_reserved=0.0, spending_by_category=spending, category_roles=roles)
    # 400 remaining, split 3:1 between Dining and Shopping
    assert result.allocations["Dining"]["allocated"] == 300.0
    assert result.allocations["Shopping"]["allocated"] == 100.0


def test_category_with_no_historical_spend_gets_zero_not_an_invented_amount():
    result = compute_budget_allocation_v2(
        spendable=1000.0, buffer_reserved=0.0,
        spending_by_category={"Rent": 0.0}, category_roles={"Rent": "fixed_essential"},
    )
    assert result.allocations["Rent"]["allocated"] == 0.0


def test_unrecognized_role_falls_back_to_discretionary_treatment():
    spending = {"Rent": 800.0, "Pottery Classes": 100.0}
    roles = {"Rent": "fixed_essential", "Pottery Classes": "unclassified"}
    result = compute_budget_allocation_v2(spendable=1000.0, buffer_reserved=0.0, spending_by_category=spending, category_roles=roles)
    assert result.allocations["Pottery Classes"]["allocated"] == 200.0
    assert result.allocations["Pottery Classes"]["is_non_neg"] is False


def test_engine_version_is_v2():
    result = compute_budget_allocation_v2(spendable=100.0, buffer_reserved=0.0, spending_by_category={}, category_roles={})
    assert result.engine_version == "budget-engine-v2"


def test_same_inputs_always_produce_the_same_output():
    spending = {"Rent": 1000.0, "Savings": 300.0, "Dining": 400.0}
    roles = {"Rent": "fixed_essential", "Savings": "savings_or_debt", "Dining": "discretionary"}
    first = compute_budget_allocation_v2(spendable=1400.0, buffer_reserved=100.0, spending_by_category=spending, category_roles=roles)
    second = compute_budget_allocation_v2(spendable=1400.0, buffer_reserved=100.0, spending_by_category=spending, category_roles=roles)
    assert first.to_dict() == second.to_dict()


def test_no_categories_does_not_error():
    result = compute_budget_allocation_v2(spendable=1000.0, buffer_reserved=0.0, spending_by_category={}, category_roles={})
    assert result.allocations == {}
    assert result.unallocated_remainder == 1000.0
