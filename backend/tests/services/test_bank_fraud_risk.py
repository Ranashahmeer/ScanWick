import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.models.accounts import Account
from app.models.bank_transactions import BankTransaction, BankTransactionDataSource, TransactionType
from app.services.bank_fraud_risk import compute_fraud_risk, redact_flags_for_loan_officer


def _txn(amount, txn_date, **overrides) -> BankTransaction:
    defaults = dict(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        transaction_date=txn_date,
        amount=int(float(amount) * 100),
        original_currency="NGN",
        type=TransactionType.credit if int(float(amount) * 100) >= 0 else TransactionType.debit,
        data_source=BankTransactionDataSource.generic_csv,
    )
    defaults.update(overrides)
    return BankTransaction(**defaults)


def _normal_transactions(count: int = 10) -> list[BankTransaction]:
    """A baseline of unremarkable, similarly-sized debits — varied amounts
    and payees so they don't trip the structuring or duplicate-payee rules
    by accident."""
    base = date(2026, 1, 1)
    return [
        _txn(f"-{12000 + i * 137}", base + timedelta(days=i), payee_normalized=f"Vendor {i}")
        for i in range(count)
    ]


def test_known_anomalous_transaction_flagged_with_human_readable_description_and_correct_score():
    """The task's explicit ask: a fixture with a known anomalous transaction,
    asserting it's flagged with a human-readable description and the
    correct score contribution."""
    transactions = _normal_transactions(10)
    anomaly = _txn("-4800000", date(2026, 1, 20), payee_normalized="Suspicious Vendor")
    transactions.append(anomaly)

    result = compute_fraud_risk(None, transactions)

    z_flags = [f for f in result["flags"] if f["flag_type"] == "z_score_anomaly"]
    assert len(z_flags) == 1
    flag = z_flags[0]
    assert flag["transaction_id"] == str(anomaly.id)
    assert "standard deviations below average" in flag["description"]  # a large debit is below the mean
    assert "2026-01-20" in flag["description"]
    assert flag["amount"] == -480000000
    assert abs(flag["z_score"]) > 3.0

    # One z_score flag -> that category's sub-score is 25 (capped scale,
    # 1 flag * 25), weighted at 0.30 per spec -> contributes exactly 7.5
    # points to the overall 0-100 score. No other category should fire on
    # this otherwise-unremarkable transaction set.
    assert result["score_breakdown"]["z_score_flags_weight"] == 0.30
    assert result["fraud_risk_score"] == 8  # round(0.30 * 25) = 7.5 -> rounds to 8
    assert result["risk_level"] == "low"


def test_structuring_flag_fires_above_threshold_and_not_below():
    base = date(2026, 1, 1)
    # 7 of 10 debits are round multiples of 1000 (70% > 30% threshold).
    round_debits = [_txn("-5000", base + timedelta(days=i), payee_normalized=f"V{i}") for i in range(7)]
    other_debits = [_txn("-1234", base + timedelta(days=i + 7), payee_normalized=f"V{i + 7}") for i in range(3)]

    result = compute_fraud_risk(None, round_debits + other_debits)
    structuring_flags = [f for f in result["flags"] if f["flag_type"] == "structuring"]
    assert len(structuring_flags) == 1
    assert "7 of 10 debits (70.0%)" in structuring_flags[0]["description"]
    assert "structuring" in structuring_flags[0]["description"].lower()


def test_structuring_does_not_fire_below_threshold():
    base = date(2026, 1, 1)
    round_debits = [_txn("-5000", base + timedelta(days=i), payee_normalized=f"V{i}") for i in range(2)]
    other_debits = [_txn("-1234", base + timedelta(days=i + 2), payee_normalized=f"V{i + 2}") for i in range(8)]

    result = compute_fraud_risk(None, round_debits + other_debits)
    assert [f for f in result["flags"] if f["flag_type"] == "structuring"] == []


def test_named_recurring_contributory_savings_is_a_positive_signal_not_structuring():
    base = date(2026, 1, 1)
    contributions = [
        _txn("-5000", base + timedelta(days=7 * index), payee_normalized="Ajo Cooperative")
        for index in range(4)
    ]

    result = compute_fraud_risk(None, contributions)

    assert [flag for flag in result["flags"] if flag["flag_type"] == "structuring"] == []
    assert result["positive_signals"] == [
        {
            "signal_type": "contributory_savings",
            "affected_transaction_count": 4,
            "cadence_days": 7.0,
            "description": (
                "Detected a recurring named contributory-savings pattern (4 ajo/esusu/adashe contributions, "
                "approximately every 7.0 days). These contributions are excluded from z-score and structuring flags."
            ),
        }
    ]


def test_named_but_irregular_savings_payments_do_not_suppress_structuring():
    base = date(2026, 1, 1)
    irregular = [
        _txn("-5000", base + timedelta(days=90 * index), payee_normalized="Esusu Group")
        for index in range(3)
    ]
    other_round_debits = [
        _txn("-5000", base + timedelta(days=4 + index), payee_normalized=f"Vendor {index}")
        for index in range(4)
    ]

    result = compute_fraud_risk(None, irregular + other_round_debits)

    assert result["positive_signals"] == []
    assert len([flag for flag in result["flags"] if flag["flag_type"] == "structuring"]) == 1


def test_duplicate_payee_flag_requires_matching_amount_date_and_payee():
    base = date(2026, 1, 5)
    dup_a = _txn("-15000", base, payee_normalized="Acme Supplies")
    dup_b = _txn("-15000", base, payee_normalized="Acme Supplies")
    not_dup_different_payee = _txn("-15000", base, payee_normalized="Beta Supplies")
    not_dup_different_date = _txn("-15000", base + timedelta(days=1), payee_normalized="Acme Supplies")

    result = compute_fraud_risk(None, [dup_a, dup_b, not_dup_different_payee, not_dup_different_date])
    dup_flags = [f for f in result["flags"] if f["flag_type"] == "duplicate_payee"]
    assert len(dup_flags) == 1
    assert dup_flags[0]["duplicate_count"] == 2
    assert "Acme Supplies" in dup_flags[0]["description"]


def test_timing_anomaly_flags_rapid_in_then_out():
    credit = _txn("2400000", date(2026, 1, 10), payee_normalized="Inward Transfer")
    debit_soon_after = _txn("-2380000", date(2026, 1, 11), payee_normalized="Outward Transfer")  # within 5% and 1 day

    result = compute_fraud_risk(None, [credit, debit_soon_after])
    timing_flags = [f for f in result["flags"] if f["flag_type"] == "timing_anomaly"]
    assert len(timing_flags) == 1
    assert "paid back out" in timing_flags[0]["description"]
    assert timing_flags[0]["days_between"] == 1


def test_timing_anomaly_does_not_fire_when_debit_too_far_in_the_future():
    credit = _txn("2400000", date(2026, 1, 1), payee_normalized="Inward Transfer")
    debit_much_later = _txn("-2400000", date(2026, 2, 1), payee_normalized="Outward Transfer")

    result = compute_fraud_risk(None, [credit, debit_much_later])
    assert [f for f in result["flags"] if f["flag_type"] == "timing_anomaly"] == []


def test_score_breakdown_always_present_with_spec_weights():
    result = compute_fraud_risk(None, _normal_transactions(3))
    assert result["score_breakdown"] == {
        "z_score_flags_weight": 0.30,
        "structuring_flags_weight": 0.30,
        "duplicate_payee_weight": 0.20,
        "timing_anomaly_weight": 0.20,
    }


def test_statement_integrity_reflects_account_balance_check():
    account_passed = Account(id=uuid.uuid4(), user_id=uuid.uuid4(), account_number_hash="x" * 64, balance_integrity_passed=True)
    account_failed = Account(id=uuid.uuid4(), user_id=uuid.uuid4(), account_number_hash="y" * 64, balance_integrity_passed=False)

    passed_result = compute_fraud_risk(account_passed, [])
    failed_result = compute_fraud_risk(account_failed, [])
    not_checked_result = compute_fraud_risk(None, [])

    assert passed_result["statement_integrity"]["balance_check"] == "passed"
    assert failed_result["statement_integrity"]["balance_check"] == "failed"
    assert not_checked_result["statement_integrity"]["balance_check"] == "not_checked"


def test_statement_integrity_date_continuity_fails_on_large_gap():
    rows = [
        _txn("-1000", date(2026, 1, 1)),
        _txn("-1000", date(2026, 3, 1)),  # ~59 day gap > 30-day threshold
    ]
    result = compute_fraud_risk(None, rows)
    assert result["statement_integrity"]["date_continuity"] == "failed"


def test_statement_integrity_sequential_ordering_fails_on_inconsistent_balance():
    rows = [
        _txn("1000", date(2026, 1, 1), balance_after=100000),
        _txn("-500", date(2026, 1, 2), balance_after=99999900),  # should be 500, not 999999
    ]
    result = compute_fraud_risk(None, rows)
    assert result["statement_integrity"]["sequential_ordering"] == "failed"


def test_statement_integrity_sequential_ordering_passes_when_consistent():
    rows = [
        _txn("1000", date(2026, 1, 1), balance_after=100000),
        _txn("-500", date(2026, 1, 2), balance_after=50000),
    ]
    result = compute_fraud_risk(None, rows)
    assert result["statement_integrity"]["sequential_ordering"] == "passed"


def test_clean_account_has_zero_score_and_low_risk():
    result = compute_fraud_risk(None, _normal_transactions(10))
    assert result["flags"] == []
    assert result["fraud_risk_score"] == 0
    assert result["risk_level"] == "low"


def test_own_account_transfers_excluded_from_fraud_detection():
    """Regression test for a real bug found during the 3.14 checkpoint:
    compute_fraud_risk used to exclude nothing by itself, so the
    standalone fraud-risk route (which only filtered is_anomalous) let
    is_own_account_transfer transactions reach z-score/structuring
    detection, while compute_loan_readiness's internal call to this same
    function DID pre-filter both -- the same function silently behaved
    differently depending on how it was reached. A large, lone
    own-account transfer should not trigger a z-score anomaly flag."""
    transactions = _normal_transactions(10) + [
        _txn("-5000000", date(2026, 1, 20), payee_normalized="Own Savings Account", is_own_account_transfer=True),
    ]

    result = compute_fraud_risk(None, transactions)

    assert all(flag["flag_type"] != "z_score_anomaly" for flag in result["flags"])


def test_anomalous_transactions_excluded_from_fraud_detection():
    transactions = _normal_transactions(10) + [
        _txn("-5000000", date(2026, 1, 20), payee_normalized="Suspicious Vendor", is_anomalous=True),
    ]

    result = compute_fraud_risk(None, transactions)

    assert all(flag["flag_type"] != "z_score_anomaly" for flag in result["flags"])


def test_redact_flags_for_loan_officer_strips_transaction_level_fields():
    """Task 5.3: a Loan Officer must never receive transaction-level
    detail. Build a real z_score flag (which embeds transaction_id,
    amount, and a description containing the transaction's date/amount)
    and confirm the redacted version has none of it."""
    transactions = _normal_transactions(10) + [
        _txn("-5000000", date(2026, 1, 20), payee_normalized="Big One-Off Vendor"),
    ]
    result = compute_fraud_risk(None, transactions)
    assert any(flag["flag_type"] == "z_score_anomaly" for flag in result["flags"])  # sanity: a real flag exists

    redacted = redact_flags_for_loan_officer(result["flags"])

    assert len(redacted) == len(result["flags"])
    for flag in redacted:
        assert "transaction_id" not in flag
        assert "amount" not in flag
        assert "description" not in flag
        assert flag["flag_type"] in {"z_score_anomaly", "structuring", "duplicate_payee", "timing_anomaly"}


def test_redact_flags_for_loan_officer_preserves_aggregate_fields():
    transactions = _normal_transactions(10) + [
        _txn("-5000000", date(2026, 1, 20), payee_normalized="Big One-Off Vendor"),
    ]
    result = compute_fraud_risk(None, transactions)

    redacted = redact_flags_for_loan_officer(result["flags"])

    z_score_flag = next(f for f in redacted if f["flag_type"] == "z_score_anomaly")
    assert "z_score" in z_score_flag
    assert "severity" in z_score_flag
