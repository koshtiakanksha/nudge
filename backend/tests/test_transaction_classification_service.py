from datetime import date
from types import SimpleNamespace

from app.services.transaction_classification_service import (
    classify_transaction,
    excluded_positive_transactions,
    income_eligible,
    merchant_key,
)


def _txn(amount, merchant="", desc="", d=date(2026, 1, 1), id_=None):
    return SimpleNamespace(
        id=id_, amount=amount, merchant_name=merchant,
        raw_description=desc, date=d,
    )


def test_payroll_deposit_is_income_eligible():
    t = _txn(1986.42, merchant="ISU PAYROLL", desc="ISU PAYROLL DIRECT DEPOSIT")
    c = classify_transaction(t)
    assert c.is_income_eligible is True
    assert c.flow_type == "income_candidate"


def test_internal_transfer_is_excluded_from_income():
    t = _txn(500.00, merchant="Online Transfer", desc="Online Transfer to Savings")
    c = classify_transaction(t)
    assert c.is_income_eligible is False
    assert c.exclusion_reason == "internal_transfer"


def test_refund_is_excluded_from_income():
    t = _txn(45.00, merchant="Amazon", desc="Amazon.com Refund")
    c = classify_transaction(t)
    assert c.is_income_eligible is False
    assert c.exclusion_reason == "refund"


def test_negative_amount_is_expense_not_income_candidate():
    t = _txn(-45.00, merchant="Whole Foods", desc="Whole Foods Market")
    c = classify_transaction(t)
    assert c.is_income_eligible is False
    assert c.flow_type == "expense"


def test_income_eligible_filters_a_mixed_batch():
    txns = [
        _txn(1986.42, merchant="ISU PAYROLL", desc="payroll deposit"),
        _txn(500.00, merchant="Transfer", desc="transfer to savings"),
        _txn(-80.00, merchant="Groceries", desc="groceries"),
    ]
    eligible = income_eligible(txns)
    assert len(eligible) == 1
    assert eligible[0].merchant_name == "ISU PAYROLL"


def test_excluded_positive_transactions_reports_reasons():
    txns = [
        _txn(1986.42, merchant="ISU PAYROLL", desc="payroll deposit"),
        _txn(500.00, merchant="Zelle", desc="zelle from roommate"),
        _txn(30.00, merchant="Amazon", desc="refund"),
    ]
    excluded = excluded_positive_transactions(txns)
    reasons = {e["reason"] for e in excluded}
    assert reasons == {"internal_transfer", "refund"}
    assert len(excluded) == 2


def test_merchant_key_normalizes_numbers_and_punctuation():
    assert merchant_key("UBER *TRIP 3829") == merchant_key("UBER TRIP 1122")
