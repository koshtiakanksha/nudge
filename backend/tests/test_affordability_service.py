from datetime import date

from app.services.affordability_service import (
    affordability_verdict,
    calculate_safe_to_spend,
    price_watch_recommendation,
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
