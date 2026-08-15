import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.accounts import Account
from app.models.bank_transactions import BankTransaction, BankTransactionDataSource, TransactionType
from app.services.bank_account_integrity import (
    compute_balance_integrity,
    compute_balance_integrity_for_rows,
    derive_balance_integrity_inputs_from_rows,
    detect_own_account_transfers,
)


@pytest.mark.parametrize(
    "opening,credits,debits,closing,expected_passed,expected_discrepancy",
    [
        # Exact match.
        (0, 340000000, 23550000, 316450000, True, None),
        # Within tolerance (0.005 off).
        (100000, 50000, 20000, 130000, True, None),
        # Exactly at the tolerance boundary (0.01) — still passes.
        (100000, 50000, 20000, 130001, True, None),
        # Just outside tolerance (0.02).
        (100000, 50000, 20000, 130002, False, 2),
        # Way off — a real discrepancy.
        (100000, 50000, 20000, 200000, False, 70000),
    ],
)
def test_compute_balance_integrity_table_driven(opening, credits, debits, closing, expected_passed, expected_discrepancy):
    result = compute_balance_integrity(opening, credits, debits, closing)
    assert result["balance_integrity_passed"] is expected_passed
    assert result["balance_discrepancy"] == expected_discrepancy


def test_balance_discrepancy_is_null_when_passed_not_zero():
    """Spec: "balance_discrepancy: Null if integrity passed" — not 0, None."""
    result = compute_balance_integrity(10000, 0, 0, 10000)
    assert result["balance_integrity_passed"] is True
    assert result["balance_discrepancy"] is None


def test_derive_inputs_from_rows_uses_first_and_last_balance_after():
    rows = [
        {"amount": 100000000, "balance_after": 100000000},
        {"amount": 240000000, "balance_after": 340000000},
        {"amount": -18400000, "balance_after": 321600000},
    ]
    inputs = derive_balance_integrity_inputs_from_rows(rows)
    assert inputs["opening_balance"] == 0  # 1000000 (balance_after) - 1000000 (amount)
    assert inputs["closing_balance"] == 321600000
    assert inputs["total_credits"] == 340000000
    assert inputs["total_debits"] == 18400000


def test_derive_inputs_returns_none_when_no_balance_column_at_all():
    rows = [{"amount": 100000, "balance_after": None}]
    assert derive_balance_integrity_inputs_from_rows(rows) is None


def test_compute_balance_integrity_for_rows_end_to_end():
    rows = [
        {"amount": 100000000, "balance_after": 100000000},
        {"amount": -5000000, "balance_after": 95000000},
    ]
    result = compute_balance_integrity_for_rows(rows)
    assert result["opening_balance"] == 0
    assert result["closing_balance"] == 95000000
    assert result["computed_closing_balance"] == 95000000
    assert result["balance_integrity_passed"] is True


def test_compute_balance_integrity_for_rows_all_none_when_no_balance_data():
    result = compute_balance_integrity_for_rows([{"amount": 100000, "balance_after": None}])
    assert result == {
        "opening_balance": None,
        "closing_balance": None,
        "computed_closing_balance": None,
        "balance_integrity_passed": None,
        "balance_discrepancy": None,
    }


def _make_account(user_id, **overrides) -> Account:
    defaults = dict(id=uuid.uuid4(), user_id=user_id, account_number_hash="x" * 64)
    defaults.update(overrides)
    return Account(**defaults)


def _make_txn(account_id, amount, txn_date, **overrides) -> BankTransaction:
    defaults = dict(
        id=uuid.uuid4(),
        account_id=account_id,
        transaction_date=txn_date,
        amount=amount,
        original_currency="NGN",
        type=TransactionType.credit if amount >= 0 else TransactionType.debit,
        data_source=BankTransactionDataSource.generic_csv,
    )
    defaults.update(overrides)
    return BankTransaction(**defaults)


async def test_detect_transfer_between_two_own_accounts(db_session):
    user_id = uuid.uuid4()
    account_a = _make_account(user_id, bank_name="GTBank")
    account_b = _make_account(user_id, bank_name="Access Bank")
    db_session.add_all([account_a, account_b])
    await db_session.commit()

    debit = _make_txn(account_a.id, -5000000, date(2026, 1, 10))
    credit = _make_txn(account_b.id, 5000000, date(2026, 1, 11))
    db_session.add_all([debit, credit])
    await db_session.commit()

    count = await detect_own_account_transfers(db_session, user_id)

    assert count == 1
    await db_session.refresh(debit)
    await db_session.refresh(credit)
    assert debit.is_own_account_transfer is True
    assert credit.is_own_account_transfer is True


async def test_does_not_match_transactions_within_the_same_account(db_session):
    user_id = uuid.uuid4()
    account = _make_account(user_id)
    db_session.add(account)
    await db_session.commit()

    debit = _make_txn(account.id, -5000000, date(2026, 1, 10))
    credit = _make_txn(account.id, 5000000, date(2026, 1, 10))
    db_session.add_all([debit, credit])
    await db_session.commit()

    count = await detect_own_account_transfers(db_session, user_id)

    assert count == 0
    await db_session.refresh(debit)
    assert debit.is_own_account_transfer is False


async def test_does_not_match_when_amounts_differ_beyond_tolerance(db_session):
    user_id = uuid.uuid4()
    account_a = _make_account(user_id)
    account_b = _make_account(user_id)
    db_session.add_all([account_a, account_b])
    await db_session.commit()

    debit = _make_txn(account_a.id, -5000000, date(2026, 1, 10))
    credit = _make_txn(account_b.id, 5000100, date(2026, 1, 10))
    db_session.add_all([debit, credit])
    await db_session.commit()

    count = await detect_own_account_transfers(db_session, user_id)
    assert count == 0


async def test_does_not_match_when_dates_too_far_apart(db_session):
    user_id = uuid.uuid4()
    account_a = _make_account(user_id)
    account_b = _make_account(user_id)
    db_session.add_all([account_a, account_b])
    await db_session.commit()

    debit = _make_txn(account_a.id, -5000000, date(2026, 1, 1))
    credit = _make_txn(account_b.id, 5000000, date(2026, 1, 10))
    db_session.add_all([debit, credit])
    await db_session.commit()

    count = await detect_own_account_transfers(db_session, user_id, date_tolerance_days=2)
    assert count == 0


async def test_returns_zero_with_only_one_account(db_session):
    user_id = uuid.uuid4()
    account = _make_account(user_id)
    db_session.add(account)
    await db_session.commit()

    count = await detect_own_account_transfers(db_session, user_id)
    assert count == 0


async def test_does_not_rematch_transactions_already_flagged(db_session):
    user_id = uuid.uuid4()
    account_a = _make_account(user_id)
    account_b = _make_account(user_id)
    db_session.add_all([account_a, account_b])
    await db_session.commit()

    debit = _make_txn(account_a.id, -5000000, date(2026, 1, 10), is_own_account_transfer=True)
    credit = _make_txn(account_b.id, 5000000, date(2026, 1, 10))
    db_session.add_all([debit, credit])
    await db_session.commit()

    count = await detect_own_account_transfers(db_session, user_id)
    assert count == 0  # debit already flagged, excluded from matching pool


async def test_unrelated_transactions_in_different_accounts_not_flagged(db_session):
    user_id = uuid.uuid4()
    account_a = _make_account(user_id)
    account_b = _make_account(user_id)
    db_session.add_all([account_a, account_b])
    await db_session.commit()

    salary = _make_txn(account_a.id, 50000000, date(2026, 1, 5))  # unrelated inflow
    rent = _make_txn(account_b.id, -12000000, date(2026, 1, 5))  # unrelated outflow
    db_session.add_all([salary, rent])
    await db_session.commit()

    count = await detect_own_account_transfers(db_session, user_id)
    assert count == 0
