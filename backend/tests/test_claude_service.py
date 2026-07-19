from app.services.claude_service import claude_service


def test_categorize_transaction_mock_mode():
    assert claude_service.mock_mode is True
    assert claude_service.categorize_transaction("Starbucks", "Food and Drink") == "Dining"
    assert claude_service.categorize_transaction("Whole Foods Market", "Groceries") == "Groceries"
    assert claude_service.categorize_transaction("Some Random Store", None) == "Other"


def test_generate_budget_mock_mode():
    # Was: non_negotiables=["Groceries"] -- generate_budget now takes
    # the full role map so compute_budget_allocation_v2 can fund in
    # priority order, not just the non-negotiable subset.
    result = claude_service.generate_budget(
        monthly_income=5000,
        spend_ceiling=4000,
        buffer_pct=0.1,
        spending_by_category={"Groceries": 400, "Dining": 200},
        category_roles={"Groceries": "fixed_essential", "Dining": "discretionary"},
    )
    assert "allocations" in result
    assert result["allocations"]["Groceries"]["is_non_neg"] is True
    assert result["buffer_reserved"] == 500.0


def test_generate_budget_funds_savings_before_discretionary():
    result = claude_service.generate_budget(
        monthly_income=2500,
        spend_ceiling=None,
        buffer_pct=0.1,
        spending_by_category={"Rent": 1000, "Savings": 300, "Dining": 400},
        category_roles={"Rent": "fixed_essential", "Savings": "savings_or_debt", "Dining": "discretionary"},
    )
    assert result["engine_version"] == "budget-engine-v2"
    assert result["allocations"]["Savings"]["allocated"] == 300.0


def test_price_verdict_mock_mode():
    result = claude_service.price_verdict(
        "Test Product", 50.0, [{"date": "2026-01-01", "price": 60}, {"date": "2026-02-01", "price": 55}]
    )
    assert result["verdict"] in ("buy_now", "wait", "overpriced")
    assert 0 <= result["confidence"] <= 100
