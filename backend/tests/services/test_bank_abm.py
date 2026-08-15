import statistics
import uuid
from datetime import date
from decimal import Decimal

from app.models.bank_transactions import BankTransaction, BankTransactionDataSource, TransactionType
from app.services.bank_abm import get_abm_response


def _txn(amount, txn_date, balance_after) -> BankTransaction:
    return BankTransaction(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        transaction_date=txn_date,
        amount=int(float(amount) * 100),
        original_currency="NGN",
        type=TransactionType.credit if int(float(amount) * 100) >= 0 else TransactionType.debit,
        balance_after=int(float(balance_after) * 100),
        data_source=BankTransactionDataSource.generic_csv,
    )


def test_abm_uses_daily_closing_balances_not_per_transaction_balances():
    """The task's explicit ask: construct a fixture where the two methods
    (daily closing balance vs. averaging every individual transaction's
    balance_after) would disagree, and prove the real computation uses the
    former."""
    transactions = [
        _txn("500000", date(2025, 4, 15), "500000"),
        _txn("500000", date(2025, 7, 15), "500000"),
        _txn("500000", date(2025, 10, 15), "500000"),
        _txn("500000", date(2026, 1, 15), "500000"),
        # 2026-04-01: three transactions the SAME day, with wildly different
        # intermediate balances -- only the LAST one (500000) is the real
        # closing balance for that day.
        _txn("10", date(2026, 4, 1), "10"),
        _txn("9999990", date(2026, 4, 1), "9999990"),
        _txn("-9999500", date(2026, 4, 1), "500000"),
    ]

    # The WRONG ("naive per-transaction") average a buggy implementation
    # would produce if it averaged every individual transaction's
    # balance_after directly, without collapsing same-day transactions
    # first.
    naive_per_transaction_average = statistics.mean(float(t.balance_after) for t in transactions)

    data, disabled_features = get_abm_response(transactions)

    assert disabled_features == []
    # The correct calculation: daily closing balances are
    # [500000, 500000, 500000, 500000, 500000] (2026-04-01 collapses to its
    # LAST transaction's balance, 500000) -- every value is 500000, so both
    # abm_3m and abm_12m must be exactly 500000.
    assert data["abm_3m"] == 50000000
    assert data["abm_12m"] == 50000000
    # And this must differ from what the wrong method would have produced --
    # proving the real calculation isn't accidentally doing the naive thing.
    assert float(data["abm_3m"]) != naive_per_transaction_average
    assert naive_per_transaction_average != 500000.0


def test_abm_disabled_with_no_balance_data():
    data, disabled_features = get_abm_response([])

    assert data is None
    assert len(disabled_features) == 1
    assert disabled_features[0]["feature_name"] == "abm"
