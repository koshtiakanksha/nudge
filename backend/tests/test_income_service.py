from datetime import date, timedelta
from types import SimpleNamespace

from app.services.income_service import detect_income, next_expected_deposits


def _txn(amount, merchant="", desc="", d=date(2026, 1, 1), id_=None):
    return SimpleNamespace(
        id=id_, amount=amount, merchant_name=merchant,
        raw_description=desc, date=d,
    )


def _monthly_payroll(months=3, amount=1986.42, start=date(2026, 1, 30)):
    txns = []
    for i in range(months):
        txns.append(_txn(
            amount, merchant="ISU PAYROLL", desc="payroll deposit",
            d=start + timedelta(days=30 * i), id_=f"payroll-{i}",
        ))
    return txns


def test_recurring_payroll_is_detected_as_a_stable_stream():
    txns = _monthly_payroll(months=3)
    profile = detect_income(txns)
    assert len(profile.streams) == 1
    assert profile.streams[0].frequency == "monthly"
    assert profile.stability == "stable"
    assert profile.estimated_monthly_income > 0


def test_single_month_of_history_with_three_occurrences_still_reads_stable():
    # Weekly payroll can produce 3+ occurrences within one calendar
    # month -- stability shouldn't require 2+ *months* if the pattern
    # itself is already consistent.
    txns = [
        _txn(500.00, merchant="ISU PAYROLL", desc="payroll", d=date(2026, 1, 2), id_="w1"),
        _txn(500.00, merchant="ISU PAYROLL", desc="payroll", d=date(2026, 1, 9), id_="w2"),
        _txn(500.00, merchant="ISU PAYROLL", desc="payroll", d=date(2026, 1, 16), id_="w3"),
    ]
    profile = detect_income(txns)
    assert profile.streams[0].frequency == "weekly"
    assert profile.stability == "stable"


def test_transfer_never_becomes_an_income_stream_even_if_recurring():
    txns = []
    for i in range(4):
        txns.append(_txn(
            500.00, merchant="Online Transfer", desc="online transfer from savings",
            d=date(2026, 1, 1) + timedelta(days=30 * i), id_=f"xfer-{i}",
        ))
    profile = detect_income(txns)
    assert profile.streams == []
    assert profile.estimated_monthly_income == 0
    assert len(profile.excluded_transactions) == 4


def test_one_off_deposit_is_unmatched_not_a_stream_and_not_excluded():
    txns = _monthly_payroll(months=3) + [
        _txn(1200.00, merchant="Freelance Client", desc="invoice payment", d=date(2026, 2, 10), id_="freelance-1"),
    ]
    profile = detect_income(txns)
    assert len(profile.streams) == 1  # payroll only
    assert any(u["merchant_name"] == "Freelance Client" for u in profile.unmatched_candidates)
    assert not any(e["merchant_name"] == "Freelance Client" for e in profile.excluded_transactions)


def test_conservative_estimate_never_exceeds_point_estimate():
    txns = _monthly_payroll(months=3)
    profile = detect_income(txns)
    assert profile.conservative_monthly_income <= profile.estimated_monthly_income + 0.01


def test_no_income_eligible_transactions_returns_zero_not_an_error():
    txns = [_txn(-50.00, merchant="Groceries", desc="groceries", d=date(2026, 1, 5))]
    profile = detect_income(txns)
    assert profile.estimated_monthly_income == 0
    assert profile.stability == "insufficient_data"


def test_next_expected_deposits_sorted_soonest_first():
    txns = _monthly_payroll(months=3) + [
        _txn(200.00, merchant="Side Gig", desc="side gig payroll", d=date(2026, 1, 5), id_="gig-1"),
        _txn(200.00, merchant="Side Gig", desc="side gig payroll", d=date(2026, 1, 19), id_="gig-2"),
        _txn(200.00, merchant="Side Gig", desc="side gig payroll", d=date(2026, 2, 2), id_="gig-3"),
    ]
    profile = detect_income(txns)
    upcoming = next_expected_deposits(profile)
    assert upcoming == sorted(upcoming, key=lambda d: d["expected_date"])
