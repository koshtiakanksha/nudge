import calendar
from datetime import date


def days_left_in_month(today: date) -> int:
    last_day = calendar.monthrange(today.year, today.month)[1]
    return max((today.replace(day=last_day) - today).days + 1, 1)


def resolve_monthly_income(user_monthly_income: float | None, income_profile=None) -> tuple[float | None, str]:
    """
    Was: safe-to-spend was blocked entirely ("Needs setup") for any user
    who hadn't manually entered a monthly income in Settings, even if
    they had months of linked transaction history income_service could
    derive a real estimate from.

    Returns (income, source) where source is "manual", "estimated", or
    "unavailable". Manual entry always wins when present -- a user who
    set it deliberately shouldn't have it silently overridden by an
    inferred number just because the inference exists.
    """
    if user_monthly_income is not None:
        return user_monthly_income, "manual"
    if income_profile is not None and getattr(income_profile, "conservative_monthly_income", 0) > 0:
        return income_profile.conservative_monthly_income, "estimated"
    return None, "unavailable"


def project_month_end_spend(mtd_spend: float, elapsed_days: int, month_days: int, upcoming_bills: float = 0) -> float:
    """
    Was: pure linear extrapolation of month-to-date spend
    (mtd_spend / elapsed_days * month_days) with upcoming_bills ignored
    entirely -- even though calculate_safe_to_spend's own `remaining`
    figure, shown right next to this one, already subtracts those same
    upcoming bills. A user with modest daily spend but a large known
    bill still due this month wouldn't get flagged "At risk" by this
    number despite the inconsistency with safe-to-spend.

    Still a linear extrapolation of past spend, not a real per-category
    spending curve (rent up front, groceries weekly, entertainment
    weekend-clustered) -- that's a bigger modeling project than this
    fix. This closes the specific inconsistency between two numbers
    that should agree on what's already known to be coming.
    """
    if elapsed_days <= 0:
        return round(upcoming_bills, 2)
    extrapolated = (mtd_spend / elapsed_days) * month_days if mtd_spend else 0
    return round(extrapolated + upcoming_bills, 2)


def calculate_safe_to_spend(
    *,
    today: date,
    month_to_date_spend: float,
    spending_ceiling: float | None,
    monthly_income: float | None,
    buffer_pct: float = 0.1,
    upcoming_bills: float = 0,
) -> dict:
    ceiling = spending_ceiling or (monthly_income * (1 - buffer_pct) if monthly_income else None)
    if ceiling is None:
        return {
            "can_calculate": False,
            "safe_to_spend_today": 0.0,
            "remaining_safe_money": 0.0,
            "spending_ceiling": None,
            "days_left": days_left_in_month(today),
            "message": "Connect a bank account or upload a statement to calculate your safe-to-spend amount.",
        }

    remaining = max(float(ceiling) - float(month_to_date_spend) - float(upcoming_bills), 0)
    days_left = days_left_in_month(today)
    safe_today = max(remaining / days_left, 0)
    return {
        "can_calculate": True,
        "safe_to_spend_today": round(safe_today, 2),
        "remaining_safe_money": round(remaining, 2),
        "spending_ceiling": round(float(ceiling), 2),
        "days_left": days_left,
        "message": f"You can safely spend ${safe_today:.0f} today and stay on track.",
    }


def affordability_verdict(
    *,
    price: float,
    category: str,
    need_or_want: str,
    safe_to_spend_today: float,
    remaining_safe_money: float,
    category_budget: float = 0,
    category_spent: float = 0,
    month_end_projection: float = 0,
    spending_ceiling: float | None = None,
    upcoming_bills: float = 0,
    product_deal_good: bool | None = None,
) -> dict:
    price = max(float(price), 0)
    safe_after = round(safe_to_spend_today - price, 2)
    remaining_after = round(remaining_safe_money - price, 2)
    category_remaining = round(category_budget - category_spent, 2)
    category_after = round(category_remaining - price, 2)
    projected_after = round(month_end_projection + price, 2)
    would_exceed_ceiling = spending_ceiling is not None and projected_after > spending_ceiling
    bill_risk = "high" if upcoming_bills > remaining_after and upcoming_bills > 0 else "medium" if remaining_after < price else "low"

    if product_deal_good is True and remaining_after < 0:
        verdict = "Good deal, bad timing"
    elif product_deal_good is True and remaining_after >= 0 and category_after >= -25:
        verdict = "Good time to buy"
    elif remaining_after >= 0 and safe_after >= 0 and category_after >= 0 and not would_exceed_ceiling:
        verdict = "Safe to buy"
    elif need_or_want == "need" and remaining_after >= 0:
        verdict = "Buy with adjustment"
    elif remaining_after >= 0 or category_after >= -50:
        verdict = "Wait"
    else:
        verdict = "Not recommended"

    actions = []
    if verdict in {"Buy with adjustment", "Wait", "Not recommended", "Good deal, bad timing"}:
        actions += ["Rebalance budget", "View forecast", "Ask Nudge"]
    if product_deal_good is not None:
        actions.append("Create price watch")
    if verdict in {"Wait", "Not recommended"}:
        actions.append("Save as purchase goal")

    explanation = _explanation(verdict, price, category, safe_to_spend_today, remaining_after, category_after)
    return {
        "verdict": verdict,
        "explanation": explanation,
        "safe_to_spend_before": round(safe_to_spend_today, 2),
        "safe_to_spend_after": safe_after,
        "remaining_before": round(remaining_safe_money, 2),
        "remaining_after": remaining_after,
        "category_impact": {
            "category": category,
            "budgeted": round(category_budget, 2),
            "spent": round(category_spent, 2),
            "remaining_before": category_remaining,
            "remaining_after": category_after,
        },
        "forecast_impact": {
            "before": round(month_end_projection, 2),
            "after": projected_after,
            "spending_ceiling": round(spending_ceiling, 2) if spending_ceiling is not None else None,
            "would_exceed_ceiling": would_exceed_ceiling,
        },
        "upcoming_bill_risk": bill_risk,
        "suggested_actions": actions,
    }


def _explanation(verdict: str, price: float, category: str, safe_today: float, remaining_after: float, category_after: float) -> str:
    if verdict == "Safe to buy":
        return f"This fits today's safe-to-spend amount and keeps {category} on track."
    if verdict == "Buy with adjustment":
        return f"You can buy this, but move money from another category or reduce future safe-to-spend by ${price:.0f}."
    if verdict == "Good deal, bad timing":
        return "The price looks good, but buying now would make your budget tight."
    if verdict == "Good time to buy":
        return "The price looks favorable and your budget can absorb it."
    if category_after < 0:
        return f"This will push {category} over budget. Consider waiting or rebalancing first."
    if remaining_after < 0:
        return f"This is above today's safe-to-spend amount of ${safe_today:.0f}. Wait until payday or rebalance."
    return "This purchase is possible, but waiting would keep more room for bills and essentials."


def deal_affordability_label(price: float | None, safe_to_spend_today: float) -> str:
    if price is None:
        return "Price not available"
    if price == 0:
        return "Free"
    if price <= safe_to_spend_today:
        return "Under today's safe-to-spend"
    return "Over today's safe-to-spend"


def price_watch_recommendation(current_price: float | None, target_price: float | None, affordability_score: float) -> str:
    if current_price is None:
        return "Limited price data"
    price_below_target = target_price is not None and current_price <= target_price
    affordable = affordability_score >= 70
    if price_below_target and affordable:
        return "Good time to buy"
    if price_below_target and not affordable:
        return "Good deal, bad timing"
    if not price_below_target and affordable:
        return "Affordable, but wait for better price"
    return "Wait"
