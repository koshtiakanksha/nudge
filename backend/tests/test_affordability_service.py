from datetime import date
from types import SimpleNamespace

from app.services.affordability_service import (
    affordability_verdict,
    calculate_safe_to_spend,
    price_watch_recommendation,
    project_month_end_spend,
    resolve_monthly_income,
)


def test_safe_to_spend_uses_ceiling_spend_and_bills():
    result = calculate_safe_to_spend(
        today=date(2026, 6, 21),
        month_to_date_spend=2100,
        spending_ceiling=3000,
        monthly_income=None,
        upcoming_bills=300,
    )

    assert result["can_calculate"] is True
    assert result["remaining_safe_money"] == 600
    assert result["safe_to_spend_today"] == 60


def test_safe_to_spend_reports_missing_setup():
    result = calculate_safe_to_spend(
        today=date(2026, 6, 21),
        month_to_date_spend=0,
        spending_ceiling=None,
        monthly_income=None,
    )

    assert result["can_calculate"] is False
    assert "Connect a bank account" in result["message"]


def test_affordability_verdict_safe_to_buy():
    result = affordability_verdict(
        price=25,
        category="Dining",
        need_or_want="want",
        safe_to_spend_today=50,
        remaining_safe_money=500,
        category_budget=300,
        category_spent=100,
        month_end_projection=2200,
        spending_ceiling=3000,
    )

    assert result["verdict"] == "Safe to buy"
    assert result["safe_to_spend_after"] == 25


def test_affordability_verdict_good_deal_bad_timing():
    result = affordability_verdict(
        price=250,
        category="Shopping",
        need_or_want="want",
        safe_to_spend_today=40,
        remaining_safe_money=100,
        category_budget=200,
        category_spent=175,
        month_end_projection=2950,
        spending_ceiling=3000,
        product_deal_good=True,
    )

    assert result["verdict"] == "Good deal, bad timing"


def test_price_watch_recommendation_combines_price_and_budget():
    assert price_watch_recommendation(80, 100, 90) == "Good time to buy"
    assert price_watch_recommendation(80, 100, 30) == "Good deal, bad timing"
    assert price_watch_recommendation(120, 100, 90) == "Affordable, but wait for better price"
    assert price_watch_recommendation(120, 100, 20) == "Wait"


def test_resolve_monthly_income_prefers_manual_when_set():
    profile = SimpleNamespace(conservative_monthly_income=5000.0)
    income, source = resolve_monthly_income(4000.0, profile)
    assert income == 4000.0
    assert source == "manual"


def test_resolve_monthly_income_falls_back_to_estimate_when_no_manual_value():
    # This is the fix: previously, no manual income meant safe-to-spend
    # was blocked entirely ("Needs setup"), even with months of
    # transaction history income_service could estimate from.
    profile = SimpleNamespace(conservative_monthly_income=3200.0)
    income, source = resolve_monthly_income(None, profile)
    assert income == 3200.0
    assert source == "estimated"


def test_resolve_monthly_income_unavailable_when_neither_exists():
    profile = SimpleNamespace(conservative_monthly_income=0.0)
    income, source = resolve_monthly_income(None, profile)
    assert income is None
    assert source == "unavailable"


def test_resolve_monthly_income_unavailable_with_no_profile_at_all():
    income, source = resolve_monthly_income(None, None)
    assert income is None
    assert source == "unavailable"


def test_project_month_end_spend_includes_upcoming_bills():
    # This is the fix: was mtd_spend/elapsed_days*month_days with
    # upcoming_bills ignored entirely, inconsistent with
    # calculate_safe_to_spend's remaining figure which DOES subtract
    # upcoming bills.
    forecast = project_month_end_spend(mtd_spend=300.0, elapsed_days=10, month_days=30, upcoming_bills=200.0)
    # extrapolated: 300/10*30 = 900, plus 200 upcoming bills = 1100
    assert forecast == 1100.0


def test_project_month_end_spend_with_no_upcoming_bills_matches_old_behavior():
    forecast = project_month_end_spend(mtd_spend=300.0, elapsed_days=10, month_days=30, upcoming_bills=0)
    assert forecast == 900.0


def test_project_month_end_spend_handles_zero_elapsed_days():
    forecast = project_month_end_spend(mtd_spend=0.0, elapsed_days=0, month_days=30, upcoming_bills=150.0)
    assert forecast == 150.0
