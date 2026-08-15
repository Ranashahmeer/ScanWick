import uuid
from datetime import date
from decimal import Decimal

from app.models.accounts import Account
from app.models.bank_transactions import BankTransaction, BankTransactionDataSource, TransactionType
from app.services.bank_dashboard import compute_dashboard_summary


def _make_account(**overrides) -> Account:
    defaults = dict(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        account_number_hash="x" * 64,
        bank_name="GTBank",
        opening_balance=100000000,
        closing_balance=150000000,
    )
    defaults.update(overrides)
    return Account(**defaults)


def _make_txn(amount, txn_date, payee=None, is_anomalous=False, is_own_account_transfer=False) -> BankTransaction:
    return BankTransaction(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        transaction_date=txn_date,
        amount=int(float(amount) * 100),
        original_currency="NGN",
        type=TransactionType.credit if int(float(amount) * 100) >= 0 else TransactionType.debit,
        payee_normalized=payee,
        is_anomalous=is_anomalous,
        is_own_account_transfer=is_own_account_transfer,
        data_source=BankTransactionDataSource.generic_csv,
    )


async def test_both_exclusion_rules_applied_to_totals():
    """The task's explicit ask: both is_anomalous and is_own_account_transfer
    exclusions applied to the totals."""
    account = _make_account()
    transactions = [
        _make_txn("100000", date(2026, 1, 5), payee="Client A"),
        _make_txn("-50000", date(2026, 1, 10), payee="Vendor B"),
        _make_txn("999999999", date(2026, 1, 15), payee="Anomaly", is_anomalous=True),
        _make_txn("888888888", date(2026, 1, 20), payee="Own Account", is_own_account_transfer=True),
    ]

    data = compute_dashboard_summary(account, transactions)

    assert data["inflows"] == 10000000
    assert data["outflows"] == 5000000


def test_balance_block_uses_account_fields():
    account = _make_account()
    data = compute_dashboard_summary(account, [])

    assert data["balance"]["opening_balance"] == 100000000
    assert data["balance"]["closing_balance"] == 150000000
    assert data["balance"]["net_change"] == 50000000


def test_balance_block_handles_missing_account():
    data = compute_dashboard_summary(None, [])

    assert data["balance"]["opening_balance"] is None
    assert data["balance"]["closing_balance"] is None
    assert data["balance"]["net_change"] is None


def test_credit_debit_split():
    account = _make_account()
    transactions = [
        _make_txn("100", date(2026, 1, 1)),
        _make_txn("200", date(2026, 1, 2)),
        _make_txn("-50", date(2026, 1, 3)),
    ]

    data = compute_dashboard_summary(account, transactions)

    assert data["credit_debit_split"] == {
        "credit_count": 2,
        "debit_count": 1,
        "credit_pct": 66.7,
        "debit_pct": 33.3,
    }


def test_top_payees_by_outflow_and_top_income_sources():
    account = _make_account()
    transactions = [
        _make_txn("-50000", date(2026, 1, 1), payee="Vendor A"),
        _make_txn("-30000", date(2026, 1, 2), payee="Vendor A"),
        _make_txn("-10000", date(2026, 1, 3), payee="Vendor B"),
        _make_txn("200000", date(2026, 1, 4), payee="Client X"),
        _make_txn("50000", date(2026, 1, 5), payee="Client Y"),
    ]

    data = compute_dashboard_summary(account, transactions)

    assert data["top_payees_by_outflow"][0] == {"payee": "Vendor A", "total_outflow": 8000000, "occurrence_count": 2}
    assert data["top_income_sources"][0] == {"payee": "Client X", "total_inflow": 20000000, "occurrence_count": 1}


def test_payees_with_no_normalized_name_are_skipped():
    account = _make_account()
    transactions = [_make_txn("-1000", date(2026, 1, 1), payee=None)]

    data = compute_dashboard_summary(account, transactions)

    assert data["top_payees_by_outflow"] == []


def test_monthly_cashflow_trend():
    account = _make_account()
    transactions = [
        _make_txn("100000", date(2026, 1, 5)),
        _make_txn("-30000", date(2026, 1, 10)),
        _make_txn("50000", date(2026, 2, 5)),
    ]

    data = compute_dashboard_summary(account, transactions)

    assert data["monthly_cashflow_trend"] == [
        {"month": "2026-01", "inflow": 10000000, "outflow": 3000000},
        {"month": "2026-02", "inflow": 5000000, "outflow": 0},
    ]
