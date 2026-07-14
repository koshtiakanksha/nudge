from app.services.budget_engine import (
    compute_budget_allocation,
    diff_allocations,
    validate_allocation,
)


def test_deterministic_same_input_same_output():
    args = (3000, 500, {"Rent": 1800, "Groceries": 500, "Dining": 300}, ["Rent"])
    r1 = compute_budget_allocation(*args)
    r2 = compute_budget_allocation(*args)
    r3 = compute_budget_allocation(*args)
    assert r1.allocations == r2.allocations == r3.allocations


def test_non_negotiable_funded_first_from_historical_spend():
    r = compute_budget_allocation(3000, 500, {"Rent": 1800, "Groceries": 500, "Dining": 300}, ["Rent"])
    assert r.allocations["Rent"]["allocated"] == 1800
    assert r.allocations["Rent"]["is_non_neg"] is True


def test_remainder_split_proportionally_by_historical_share():
    r = compute_budget_allocation(3000, 500, {"Rent": 1800, "Groceries": 500, "Dining": 300}, ["Rent"])
    # Groceries:Dining historical ratio is 500:300 -- allocated should match
    ratio_hist = 500 / 300
    ratio_alloc = r.allocations["Groceries"]["allocated"] / r.allocations["Dining"]["allocated"]
    assert abs(ratio_hist - ratio_alloc) < 0.01


def test_allocations_never_exceed_spendable():
    r = compute_budget_allocation(3000, 500, {"Rent": 1800, "Groceries": 500, "Dining": 300}, ["Rent"])
    total = sum(v["allocated"] for v in r.allocations.values())
    assert total <= 3000 + 0.01


def test_non_negotiable_with_no_historical_data_gets_zero_not_invented():
    r = compute_budget_allocation(2000, 200, {"Groceries": 400, "Dining": 200}, ["Rent"])
    assert r.allocations["Rent"]["allocated"] == 0.0
    assert r.allocations["Rent"]["is_non_neg"] is True


def test_non_negotiables_exceeding_spendable_are_scaled_down_not_overdrawn():
    r = compute_budget_allocation(1000, 500, {"Rent": 1800}, ["Rent"])
    assert r.allocations["Rent"]["allocated"] == 1000.0
    assert r.non_negotiables_constrained is True


def test_empty_spending_history_returns_empty_allocations_not_a_fabricated_set():
    r = compute_budget_allocation(2500, 400, {}, [])
    assert r.allocations == {}
    assert r.unallocated_remainder == 2500


def test_categories_with_zero_historical_weight_split_evenly():
    r = compute_budget_allocation(1000, 0, {"A": 0, "B": 0}, [])
    assert r.allocations["A"]["allocated"] == r.allocations["B"]["allocated"] == 500.0


def test_validate_allocation_catches_over_budget():
    bad = {"Groceries": {"allocated": 5000, "is_non_neg": False}}
    is_valid, issues = validate_allocation(bad, spendable=1000, non_negotiables=[])
    assert is_valid is False
    assert any("exceeds spendable" in i for i in issues)


def test_validate_allocation_flags_missing_non_negotiable_as_hard_failure():
    is_valid, issues = validate_allocation({}, spendable=1000, non_negotiables=["Rent"])
    assert is_valid is False
    assert any("missing" in i for i in issues)


def test_validate_allocation_zero_funded_non_negotiable_is_warning_not_failure():
    allocations = {"Rent": {"allocated": 0.0, "is_non_neg": True}}
    is_valid, issues = validate_allocation(allocations, spendable=1000, non_negotiables=["Rent"])
    assert is_valid is True
    assert any(i.startswith("WARNING") for i in issues)


def test_diff_allocations_reports_changed_categories_only():
    previous = {"Rent": {"allocated": 1800, "is_non_neg": True}, "Groceries": {"allocated": 500, "is_non_neg": False}}
    current = {"Rent": {"allocated": 1800, "is_non_neg": True}, "Groceries": {"allocated": 650, "is_non_neg": False}}
    changes = diff_allocations(previous, current)
    assert len(changes) == 1
    assert changes[0]["category"] == "Groceries"
    assert changes[0]["delta"] == 150.0


def test_diff_allocations_with_no_previous_returns_empty():
    current = {"Rent": {"allocated": 1800, "is_non_neg": True}}
    assert diff_allocations(None, current) == []
