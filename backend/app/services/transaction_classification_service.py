"""
Shared transaction classification service.

Single source of truth for what a transaction *is* -- transfer, refund,
reimbursement, fee, or a genuine income/expense event -- before any
other service (income detection, category baselines, budget
generation) uses it.

This exists specifically because a recurring transfer between two of a
user's own accounts (e.g. savings -> checking) has the exact same shape
as a recurring paycheck: positive amount, regular interval, consistent
size. Classification has to happen before any grouping logic tries to
learn what "income" looks like for a given user, or a transfer gets
learned as a paycheck.

Both Plaid-synced transactions (app.models.transaction.Transaction) and
parsed statement uploads (app.services.statement_analysis_service
.ParsedTransaction) are duck-typed the same way here -- anything with
.amount, .merchant_name, .raw_description (or .description), and .date
works. This is what makes the classification shared rather than
per-source: it doesn't care which pipeline the transaction came from.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

TRANSFER_KEYWORDS = [
    "transfer", "zelle", "venmo", "cash app", "cashapp", "paypal transfer",
    "xfer", "internal transfer", "acct transfer", "account transfer",
    "online transfer", "to savings", "from savings", "to checking", "from checking",
]
REFUND_KEYWORDS = [
    "refund", "return", "reversal", "chargeback", "credit adjustment", "merchant credit",
]
REIMBURSEMENT_KEYWORDS = [
    "reimbursement", "reimburse", "expense report", "expense reimb",
]
FEE_KEYWORDS = ["fee", "overdraft", "interest charge", "finance charge"]
INCOME_KEYWORDS = ["payroll", "salary", "direct deposit", "paycheck", "pay period"]

FLOW_TRANSFER = "transfer"
FLOW_REFUND = "refund"
FLOW_REIMBURSEMENT = "reimbursement"
FLOW_FEE = "fee"
FLOW_INCOME_CANDIDATE = "income_candidate"
FLOW_EXPENSE = "expense"


@dataclass
class Classification:
    flow_type: str
    is_income_eligible: bool
    exclusion_reason: str | None
    confidence: float


def merchant_key(value: str | None) -> str:
    """Normalize a merchant/description string into a stable grouping key.

    Moved here (out of statement_analysis_service) because grouping
    logic in income_service and future category_profile_service needs
    the exact same normalization regardless of transaction source.
    """
    text = (value or "").lower()
    text = re.sub(r"\d+", "", text)
    text = re.sub(r"[^a-z ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()[:80] or "unknown"


def _text_for(t) -> str:
    merchant = getattr(t, "merchant_name", None) or ""
    desc = getattr(t, "raw_description", None) or getattr(t, "description", None) or ""
    return f"{merchant} {desc}".lower()


def classify_transaction(t) -> Classification:
    """
    Classify a single transaction.

    Order matters: transfers, refunds, reimbursements, and fees are all
    checked -- and excluded -- before a positive amount is ever
    considered an income candidate.
    """
    amount = float(getattr(t, "amount", 0) or 0)
    text = _text_for(t)

    if any(k in text for k in TRANSFER_KEYWORDS):
        return Classification(FLOW_TRANSFER, False, "internal_transfer", 0.85)

    if amount > 0 and any(k in text for k in REFUND_KEYWORDS):
        return Classification(FLOW_REFUND, False, "refund", 0.8)

    if amount > 0 and any(k in text for k in REIMBURSEMENT_KEYWORDS):
        return Classification(FLOW_REIMBURSEMENT, False, "reimbursement", 0.75)

    if any(k in text for k in FEE_KEYWORDS):
        return Classification(FLOW_FEE, False, "fee", 0.8)

    if amount > 0:
        if any(k in text for k in INCOME_KEYWORDS):
            return Classification(FLOW_INCOME_CANDIDATE, True, None, 0.9)
        # Positive amount, no transfer/refund/reimbursement/payroll
        # signal in the text -- still a candidate, just lower
        # confidence until income_service confirms it actually recurs.
        return Classification(FLOW_INCOME_CANDIDATE, True, None, 0.55)

    return Classification(FLOW_EXPENSE, False, None, 0.7)


def classify_transactions(transactions: list) -> dict:
    """Classify a batch. Keyed by .id when present (ORM Transaction),
    otherwise by id() of the object (ParsedTransaction has no .id yet
    at analysis time, before it's persisted)."""
    result = {}
    for t in transactions:
        key = getattr(t, "id", None)
        if key is None:
            key = id(t)
        result[key] = classify_transaction(t)
    return result


def income_eligible(transactions: list) -> list:
    """Transactions that pass classification as income candidates --
    excludes transfers, refunds, reimbursements, and fees. Does NOT mean
    "confirmed recurring income" -- that's income_service's job."""
    return [t for t in transactions if classify_transaction(t).is_income_eligible]


def excluded_positive_transactions(transactions: list) -> list[dict]:
    """Positive-amount transactions excluded from income consideration,
    with the reason -- so the exclusion is visible in an evidence/UI
    layer instead of silently dropped."""
    excluded = []
    for t in transactions:
        amount = float(getattr(t, "amount", 0) or 0)
        if amount <= 0:
            continue
        c = classify_transaction(t)
        if not c.is_income_eligible:
            excluded.append({
                "transaction_id": getattr(t, "id", None),
                "merchant_name": getattr(t, "merchant_name", None),
                "amount": round(amount, 2),
                "date": getattr(t, "date", None),
                "reason": c.exclusion_reason or c.flow_type,
            })
    return excluded


transaction_classification_service = {
    "merchant_key": merchant_key,
    "classify_transaction": classify_transaction,
    "classify_transactions": classify_transactions,
    "income_eligible": income_eligible,
    "excluded_positive_transactions": excluded_positive_transactions,
}
