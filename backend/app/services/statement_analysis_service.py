import csv
import io
import re
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from app.services.budget_engine import compute_budget_allocation
from app.services.category_profile_service import build_category_profiles
from app.services.category_role_service import is_non_negotiable, roles_for_categories
from app.services.claude_service import claude_service
from app.services.income_service import detect_income
from app.services.transaction_classification_service import (
    income_eligible,
    merchant_key,
)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".csv", ".txt", ".xlsx", ".pdf"}
# Matches User.buffer_pct's default (app/models/user.py) -- the
# statement-upload flow doesn't have a user record to read a real
# per-user buffer from here, so it falls back to the same default the
# Plaid-linked flow starts new users at.
DEFAULT_BUDGET_BUFFER_PCT = 0.10

DEFAULT_CATEGORIES = [
    "Rent",
    "Utilities",
    "Groceries",
    "Dining",
    "Transportation",
    "Shopping",
    "Travel",
    "Entertainment",
    "Healthcare",
    "Education",
    "Subscriptions",
    "Transfers",
    "Income",
    "Savings",
    "Debt Payments",
    "Fees",
    "Other",
]

CATEGORY_KEYWORDS = {
    "Rent": ["rent", "apartment", "property management", "landlord"],
    "Utilities": ["electric", "utility", "water", "gas bill", "comcast", "verizon", "at&t", "internet"],
    "Groceries": ["whole foods", "trader joe", "safeway", "kroger", "grocery", "market"],
    "Dining": ["starbucks", "restaurant", "cafe", "coffee", "doordash", "grubhub", "chipotle"],
    "Transportation": ["uber", "lyft", "shell", "chevron", "gas", "metro", "parking", "transit"],
    "Shopping": ["amazon", "target", "walmart", "best buy", "store"],
    "Travel": ["airbnb", "hotel", "marriott", "hilton", "delta", "united", "airlines", "southwest"],
    "Entertainment": ["netflix", "spotify", "hulu", "amc", "theater", "cinema"],
    "Healthcare": ["cvs", "walgreens", "pharmacy", "doctor", "clinic", "medical"],
    "Education": ["tuition", "school", "university", "coursera", "udemy"],
    "Subscriptions": ["subscription", "membership", "apple.com/bill", "spotify", "netflix"],
    "Transfers": ["transfer", "zelle", "venmo", "cash app", "paypal"],
    "Income": ["payroll", "salary", "direct deposit", "deposit"],
    "Savings": ["savings", "investment", "brokerage"],
    "Debt Payments": ["loan", "credit card payment", "student loan", "mortgage"],
    "Fees": ["fee", "overdraft", "atm"],
}

DATE_COLUMNS = ["date", "transaction date", "posted date", "post date"]
DESC_COLUMNS = ["description", "memo", "details", "transaction", "name"]
MERCHANT_COLUMNS = ["merchant", "merchant name", "payee"]
DEBIT_COLUMNS = ["debit", "withdrawal", "withdrawals", "charge"]
CREDIT_COLUMNS = ["credit", "deposit", "deposits"]
AMOUNT_COLUMNS = ["amount", "transaction amount"]
CATEGORY_COLUMNS = ["category"]


@dataclass
class ParsedTransaction:
    date: date
    description: str
    merchant_name: str | None
    amount: float
    transaction_type: str
    category: str
    raw_description: str
    confidence_score: float
    raw_data: dict
    currency: str = "USD"


def validate_upload(filename: str, size: int) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported file type. Upload CSV, TXT, XLSX, or PDF.")
    if size > MAX_UPLOAD_BYTES:
        raise ValueError("File is too large. Upload statements smaller than 10 MB.")
    return ext


def parse_statement_bytes(filename: str, content: bytes, category_rules: dict[str, str], mapping: dict | None = None) -> list[ParsedTransaction]:
    ext = validate_upload(filename, len(content))
    if ext == ".pdf":
        raise ValueError("PDF parsing is not enabled yet. Export your statement as CSV for the most accurate import.")
    if ext == ".xlsx":
        try:
            df = pd.read_excel(io.BytesIO(content))
        except Exception as exc:
            raise ValueError("Could not read this XLSX file. Try exporting it as CSV.") from exc
    else:
        text = content.decode("utf-8-sig", errors="replace")
        dialect = csv.Sniffer().sniff(text[:4096]) if "," in text[:4096] or "\t" in text[:4096] else csv.excel
        df = pd.read_csv(io.StringIO(text), dialect=dialect)

    if df.empty:
        return []

    columns = {str(c).strip().lower(): c for c in df.columns}
    mapping = mapping or {}
    date_col = _mapped_column(df.columns, mapping.get("date")) or _find_column(columns, DATE_COLUMNS)
    desc_col = _mapped_column(df.columns, mapping.get("description")) or _find_column(columns, DESC_COLUMNS)
    merchant_col = _mapped_column(df.columns, mapping.get("merchant")) or _find_column(columns, MERCHANT_COLUMNS)
    debit_col = _mapped_column(df.columns, mapping.get("debit")) or _find_column(columns, DEBIT_COLUMNS)
    credit_col = _mapped_column(df.columns, mapping.get("credit")) or _find_column(columns, CREDIT_COLUMNS)
    amount_col = _mapped_column(df.columns, mapping.get("amount")) or _find_column(columns, AMOUNT_COLUMNS)
    category_col = _mapped_column(df.columns, mapping.get("category")) or _find_column(columns, CATEGORY_COLUMNS)

    if not date_col or not (desc_col or merchant_col) or not (amount_col or debit_col or credit_col):
        raise ValueError("We could not identify the date, description, and amount columns. Manual column mapping is needed.")

    parsed: list[ParsedTransaction] = []
    for _, row in df.iterrows():
        txn_date = pd.to_datetime(row.get(date_col), errors="coerce")
        if pd.isna(txn_date):
            continue
        description = _clean_text(row.get(desc_col) if desc_col else row.get(merchant_col))
        merchant = _clean_text(row.get(merchant_col)) or _guess_merchant(description)
        amount = _parse_amount(row.get(amount_col)) if amount_col else 0
        debit = _parse_amount(row.get(debit_col)) if debit_col else 0
        credit = _parse_amount(row.get(credit_col)) if credit_col else 0
        if debit or credit:
            amount = credit - abs(debit)
        if amount == 0:
            continue
        raw_category = _clean_text(row.get(category_col)) if category_col else None
        category, confidence = categorize_transaction(merchant or description, raw_category, amount, category_rules)
        parsed.append(
            ParsedTransaction(
                date=txn_date.date(),
                description=description,
                merchant_name=merchant,
                amount=round(amount, 2),
                transaction_type=transaction_type_for(amount, description),
                category=category,
                raw_description=description,
                confidence_score=confidence,
                raw_data={str(k): None if pd.isna(v) else str(v) for k, v in row.to_dict().items()},
            )
        )
    return parsed


def _find_column(columns: dict[str, str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return columns[candidate]
    for key, original in columns.items():
        if any(candidate in key for candidate in candidates):
            return original
    return None


def _mapped_column(columns, requested: str | None) -> str | None:
    if not requested:
        return None
    for column in columns:
        if str(column).strip().lower() == requested.strip().lower():
            return column
    return None


def _parse_amount(value) -> float:
    if value is None or pd.isna(value):
        return 0.0
    text = str(value).strip()
    if not text:
        return 0.0
    negative = text.startswith("(") and text.endswith(")")
    text = text.replace("$", "").replace(",", "").replace("(", "").replace(")", "")
    try:
        amount = float(text)
    except ValueError:
        return 0.0
    return -abs(amount) if negative else amount


def _clean_text(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _guess_merchant(description: str) -> str | None:
    cleaned = re.sub(r"\b\d{2,}\b", "", description)
    cleaned = re.sub(r"[*#][A-Za-z0-9]+", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()[:120] or None


def categorize_transaction(merchant: str, raw_category: str | None, amount: float, category_rules: dict[str, str]) -> tuple[str, float]:
    key = merchant_key(merchant)
    if key in category_rules:
        return category_rules[key], 0.98
    if amount > 0:
        return "Income", 0.9
    text = f"{merchant} {raw_category or ''}".lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category, 0.82
    ai_category = claude_service.categorize_transaction(merchant, raw_category)
    mapped = _map_ai_category(ai_category)
    return mapped, 0.58 if mapped == "Other" else 0.68


def _map_ai_category(category: str) -> str:
    aliases = {"Health & Fitness": "Healthcare", "Utilities & Bills": "Utilities"}
    return aliases.get(category, category if category in DEFAULT_CATEGORIES else "Other")


def transaction_type_for(amount: float, description: str) -> str:
    text = description.lower()
    if amount > 0:
        if "refund" in text:
            return "refund"
        return "income" if any(word in text for word in ["payroll", "salary", "deposit"]) else "credit"
    if "transfer" in text or "zelle" in text or "venmo" in text:
        return "transfer"
    if "fee" in text or "overdraft" in text:
        return "fee"
    return "debit"


def summarize_transactions(transactions: list) -> dict:
    included = [t for t in transactions if not getattr(t, "is_ignored", False)]
    # Was: sum(t.amount for t in included if t.amount > 0) -- counted
    # every positive transaction as income, including transfers between
    # a user's own accounts and refunds. income_eligible() excludes
    # those via transaction_classification_service before summing.
    income = sum(float(t.amount) for t in income_eligible(included))
    spending = sum(abs(float(t.amount)) for t in included if float(t.amount) < 0)
    dates = [t.date for t in included]
    days = max((max(dates) - min(dates)).days + 1, 1) if dates else 1
    months = sorted({(t.date.year, t.date.month) for t in included})
    return {
        "total_income": round(income, 2),
        "total_spending": round(spending, 2),
        "net_cash_flow": round(income - spending, 2),
        "average_daily_spending": round(spending / days, 2),
        "average_weekly_spending": round((spending / days) * 7, 2),
        "savings_rate": round((income - spending) / income, 4) if income else None,
        "transaction_count": len(included),
        "months_of_history": len(months),
    }


def category_totals(transactions: list) -> list[dict]:
    totals: dict[str, dict] = defaultdict(lambda: {"amount": 0.0, "transaction_count": 0})
    for t in transactions:
        if getattr(t, "is_ignored", False) or float(t.amount) >= 0:
            continue
        cat = t.nudge_category or "Other"
        totals[cat]["amount"] += abs(float(t.amount))
        totals[cat]["transaction_count"] += 1
    return [{"category": k, "amount": round(v["amount"], 2), "transaction_count": v["transaction_count"]} for k, v in sorted(totals.items(), key=lambda x: x[1]["amount"], reverse=True)]


def merchant_totals(transactions: list) -> list[dict]:
    totals: dict[str, dict] = defaultdict(lambda: {"amount": 0.0, "transaction_count": 0})
    for t in transactions:
        if getattr(t, "is_ignored", False) or float(t.amount) >= 0:
            continue
        merchant = t.merchant_name or "Unknown merchant"
        totals[merchant]["amount"] += abs(float(t.amount))
        totals[merchant]["transaction_count"] += 1
    return [{"merchant_name": k, "amount": round(v["amount"], 2), "transaction_count": v["transaction_count"]} for k, v in sorted(totals.items(), key=lambda x: x[1]["amount"], reverse=True)]


def monthly_trends(transactions: list) -> list[dict]:
    totals: dict[str, dict] = defaultdict(lambda: {"income": 0.0, "spending": 0.0})
    for t in transactions:
        if getattr(t, "is_ignored", False):
            continue
        month = t.date.strftime("%Y-%m")
        if float(t.amount) > 0:
            totals[month]["income"] += float(t.amount)
        else:
            totals[month]["spending"] += abs(float(t.amount))
    return [{"month": m, "income": round(v["income"], 2), "spending": round(v["spending"], 2)} for m, v in sorted(totals.items())]


def detect_recurring(transactions: list) -> list[dict]:
    by_merchant: dict[str, list] = defaultdict(list)
    for t in transactions:
        if getattr(t, "is_ignored", False) or float(t.amount) >= 0:
            continue
        by_merchant[merchant_key(t.merchant_name or t.raw_description)].append(t)
    recurring = []
    for _, rows in by_merchant.items():
        if len(rows) < 2:
            continue
        rows = sorted(rows, key=lambda t: t.date)
        amounts = [abs(float(t.amount)) for t in rows]
        avg_amount = sum(amounts) / len(amounts)
        if any(abs(a - avg_amount) > max(5, avg_amount * 0.2) for a in amounts):
            continue
        deltas = [(rows[i].date - rows[i - 1].date).days for i in range(1, len(rows))]
        avg_delta = sum(deltas) / len(deltas) if deltas else 30
        frequency = "monthly" if 24 <= avg_delta <= 38 else "weekly" if 5 <= avg_delta <= 9 else "recurring"
        recurring.append({
            "merchant_name": rows[-1].merchant_name or "Unknown merchant",
            "amount": round(avg_amount, 2),
            "frequency": frequency,
            "next_expected_date": rows[-1].date + timedelta(days=round(avg_delta or 30)),
            "category": rows[-1].nudge_category,
            "confidence_score": 0.82 if frequency in {"monthly", "weekly"} else 0.62,
        })
    return recurring


def detect_soft_anomalies(transactions: list) -> list[dict]:
    anomalies = []
    by_merchant = defaultdict(list)
    seen_merchants = set()
    location_counter = Counter()
    for t in sorted(transactions, key=lambda row: row.date):
        if getattr(t, "is_ignored", False):
            continue
        key = merchant_key(t.merchant_name or t.raw_description)
        amount_abs = abs(float(t.amount))
        previous = by_merchant[key]
        if not previous and key not in seen_merchants and float(t.amount) < 0:
            anomalies.append({"transaction_id": t.id, "anomaly_type": "new_merchant", "explanation": "New merchant detected. This looks different from your usual pattern.", "severity": "low", "merchant_name": t.merchant_name, "amount": float(t.amount)})
        if previous:
            avg = sum(abs(float(row.amount)) for row in previous) / len(previous)
            if amount_abs > avg * 1.8 and amount_abs - avg > 25:
                anomalies.append({"transaction_id": t.id, "anomaly_type": "unusual_amount", "explanation": f"This charge is higher than your usual {t.merchant_name or 'merchant'} spending.", "severity": "medium", "merchant_name": t.merchant_name, "amount": float(t.amount)})
        by_merchant[key].append(t)
        seen_merchants.add(key)
        if t.location_city or t.location_state or t.location_country:
            location_counter[(t.location_city, t.location_state, t.location_country)] += 1

    for i, left in enumerate(transactions):
        for right in transactions[i + 1:]:
            if left.date == right.date and abs(float(left.amount) - float(right.amount)) < 0.01 and merchant_key(left.merchant_name) == merchant_key(right.merchant_name):
                anomalies.append({"transaction_id": right.id, "anomaly_type": "duplicate", "explanation": "Possible duplicate transaction detected.", "severity": "medium", "merchant_name": right.merchant_name, "amount": float(right.amount)})

    travel = detect_travel(transactions)
    anomalies.extend(travel)
    return anomalies[:30]


def detect_travel(transactions: list) -> list[dict]:
    travel_keywords = ["hotel", "airbnb", "airline", "delta", "united", "marriott", "hilton"]
    matches = [t for t in transactions if any(word in ((t.merchant_name or "") + " " + (t.raw_description or "")).lower() for word in travel_keywords)]
    if len(matches) < 2:
        return []
    start = min(t.date for t in matches)
    end = max(t.date for t in matches)
    total = sum(abs(float(t.amount)) for t in matches if float(t.amount) < 0)
    return [{
        "transaction_id": matches[0].id,
        "anomaly_type": "possible_travel",
        "explanation": f"Possible travel spending detected from {start.isoformat()} to {end.isoformat()} totaling ${total:.2f}. Was this a trip?",
        "severity": "low",
        "merchant_name": "Travel pattern",
        "amount": -round(total, 2),
    }]


def budget_recommendations(transactions: list, target_month: date) -> dict:
    trends = monthly_trends(transactions)
    summary = summarize_transactions(transactions)
    non_travel = [t for t in transactions if not getattr(t, "is_anomaly", False) and (t.nudge_category != "Travel")]
    categories = category_totals(non_travel)
    months = max(summary["months_of_history"], 1)
    income_profile = detect_income(transactions)
    # Conservative estimate is what the budget should plan around --
    # falls back to the old flat total/months average only when
    # income_service has nothing to go on at all (e.g. one transaction).
    income_estimate = income_profile.conservative_monthly_income or (
        round(summary["total_income"] / months, 2) if summary["total_income"] else 0
    )
    # Was: monthly_avg = item["amount"] / months, with a hardcoded 10%
    # haircut applied only to Dining/Shopping/Entertainment and nothing
    # else -- one flat average for every category, easily skewed by a
    # single expensive month. category_profiles gives each category its
    # own median, recency-weighted average, and a buffer sized to how
    # volatile (and how essential) that specific category actually is.
    category_profiles = build_category_profiles(non_travel)

    # Was: sum every category's suggested amount and call whatever was
    # left over "Savings" -- nothing checked that sum against income at
    # all, so total_budget could exceed income_estimate with no
    # correction. compute_budget_allocation is the same deterministic,
    # income-respecting engine budgets.py's /budgets/generate already
    # uses: non-negotiables are funded first, everything is capped to
    # what's actually spendable, and it's flagged (not silently
    # overspent) if non-negotiables alone don't fit.
    #
    # Note: non-negotiables here are name-based only (no user_id/db
    # session in this function to read real BudgetCategory overrides,
    # same limitation category_profile_service already documents) --
    # per-user overrides land when this flow gets real DB access.
    roles = roles_for_categories(list(category_profiles.keys()))
    non_negotiables = [cat for cat, role in roles.items() if is_non_negotiable(role)]
    spending_by_category = {cat: profile.suggested_amount for cat, profile in category_profiles.items()}
    buffer_reserved = round(income_estimate * DEFAULT_BUDGET_BUFFER_PCT, 2) if income_estimate else 0.0
    spendable = max(round(income_estimate - buffer_reserved, 2), 0.0)
    engine_result = compute_budget_allocation(spendable, buffer_reserved, spending_by_category, non_negotiables)

    warnings = []
    if engine_result.non_negotiables_constrained:
        warnings.append("Non-negotiable categories alone exceed your estimated income; they were scaled down to fit.")

    recs = []
    for item in categories:
        profile = category_profiles.get(item["category"])
        alloc = engine_result.allocations.get(item["category"])
        recommended = alloc["allocated"] if alloc else round(item["amount"] / months, 2)
        if profile is None:
            reasoning = f"Your average {item['category']} spend is ${item['amount'] / months:.2f}/month based on uploaded history."
            confidence_score = 0.75 if months >= 3 else 0.55
        elif profile.used_recurring_amount:
            reasoning = (
                f"{item['category']} recurs at ${profile.recurring_component:.2f}/month "
                f"across {profile.months_of_history} month(s), so that recurring amount is used directly."
            )
            confidence_score = profile.confidence
        else:
            low, high = profile.typical_range
            reasoning = (
                f"Median {item['category']} spend was ${profile.median_monthly_spend:.2f}/month "
                f"(typical range ${low:.2f}-${high:.2f}) across {profile.months_of_history} "
                f"month(s), with a {profile.buffer_pct * 100:.0f}% buffer applied."
            )
            confidence_score = profile.confidence
        if recommended > max(income_estimate * 0.25, 500) and income_estimate:
            warnings.append(f"{item['category']} is a high spending category compared with your estimated income.")
        recs.append({
            "category": item["category"],
            "recommended_amount": round(recommended, 2),
            "reasoning": reasoning,
            "confidence_score": confidence_score,
        })
    total_budget = round(sum(r["recommended_amount"] for r in recs), 2)
    if income_estimate:
        recs.append({
            "category": "Savings",
            "recommended_amount": round(max(engine_result.unallocated_remainder, 0), 2),
            "reasoning": "Recommended as the remaining cash after estimated expenses and buffer.",
            "confidence_score": 0.65,
        })
    return {
        "month": target_month,
        "income_estimate": income_estimate,
        "income_profile": income_profile.to_dict(),
        "total_budget": total_budget,
        "recommendations": recs,
        "category_profiles": {k: v.to_dict() for k, v in category_profiles.items()},
        "allocation": engine_result.to_dict(),
        "warnings": warnings,
        "explanation": "Built from uploaded statement history using per-category medians, recency-weighted averages, and volatility-aware buffers, capped to your estimated spendable income.",
        "not_enough_history": summary["months_of_history"] < 2,
    }


def income_summary(transactions: list) -> dict:
    """Direct access to income_service's output for this transaction
    set -- for API routes or the chat/affordability layer that need the
    income profile without generating a full budget recommendation."""
    return detect_income(transactions).to_dict()


def insights(transactions: list) -> list[dict]:
    result = []
    summary = summarize_transactions(transactions)
    cats = category_totals(transactions)
    recurring = detect_recurring(transactions)
    if cats:
        top = cats[0]
        result.append({"title": f"Highest category: {top['category']}", "detail": f"You spent ${top['amount']:.2f} on {top['category']} across {top['transaction_count']} transactions.", "severity": "info"})
    if recurring:
        total = sum(r["amount"] for r in recurring)
        result.append({"title": "Recurring expenses found", "detail": f"You have {len(recurring)} likely recurring expenses totaling about ${total:.2f}.", "severity": "info"})
    if summary["savings_rate"] is not None:
        result.append({"title": "Savings rate", "detail": f"Your savings rate from uploaded history is {summary['savings_rate'] * 100:.0f}%.", "severity": "info"})
    if summary["months_of_history"] < 2:
        result.append({"title": "More history improves predictions", "detail": "Not enough history yet. Upload at least 2 to 3 months of statements for better predictions.", "severity": "low"})
    return result


statement_analysis_service = {
    "validate_upload": validate_upload,
    "parse_statement_bytes": parse_statement_bytes,
    "merchant_key": merchant_key,
    "summarize_transactions": summarize_transactions,
    "category_totals": category_totals,
    "merchant_totals": merchant_totals,
    "monthly_trends": monthly_trends,
    "detect_recurring": detect_recurring,
    "detect_soft_anomalies": detect_soft_anomalies,
    "budget_recommendations": budget_recommendations,
    "income_summary": income_summary,
    "insights": insights,
}
