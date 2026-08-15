import uuid
from datetime import date
from decimal import Decimal

from app.models.accounts import Account
from app.models.bank_transactions import BankTransaction, BankTransactionDataSource, TransactionType
from app.services.bank_cashflow_analysis import compute_cashflow_analysis


def _txn(amount, txn_date, description=None, payee=None, balance_after=None) -> BankTransaction:
    return BankTransaction(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        transaction_date=txn_date,
        amount=int(float(amount) * 100),
        original_currency="NGN",
        type=TransactionType.credit if int(float(amount) * 100) >= 0 else TransactionType.debit,
        description=description,
        payee_normalized=payee,
        balance_after=int(float(balance_after) * 100) if balance_after is not None else None,
        data_source=BankTransactionDataSource.generic_csv,
    )


def _fixture_with_known_recurring_and_variable() -> list[BankTransaction]:
    """3 months of rent (recurring, business) + 3 months of Netflix
    (recurring, personal) + a one-off ATM withdrawal and a one-off
    supermarket POS purchase (both variable)."""
    rows = []
    balance = 500000000
    for month in (1, 2, 3):
        d = date(2026, month, 5)
        balance -= 50000000
        rows.append(_txn("-500000", d, "Standing Order - Office Rent Payment", "Landlord Co", balance))
        balance -= 500000
        rows.append(_txn("-5000", d, "Netflix Subscription", "Netflix", balance))
    balance -= 2000000
    rows.append(_txn("-20000", date(2026, 3, 10), "ATM Cash Withdrawal", "ATM", balance))
    balance -= 1000000
    rows.append(_txn("-10000", date(2026, 3, 12), "POS Purchase - Supermarket Visit", "Supermarket", balance))
    balance += 100000000
    rows.append(_txn("1000000", date(2026, 3, 1), "Salary Credit", "Employer", balance))
    return rows


def test_recurring_vs_variable_against_known_fixture():
    """The task's explicit ask: a fixture with known recurring vs. variable
    outflows."""
    account = Account(id=uuid.uuid4(), user_id=uuid.uuid4(), account_number_hash="a" * 64, closing_balance=446500000)
    transactions = _fixture_with_known_recurring_and_variable()

    data = compute_cashflow_analysis(account, transactions)

    # Recurring: rent (3x500000) + Netflix (3x5000) = 1,515,000. Variable: ATM + supermarket = 30,000.
    assert data["recurring_vs_variable"]["recurring_total"] == 151500000
    assert data["recurring_vs_variable"]["variable_total"] == 3000000
    assert data["recurring_vs_variable"]["recurring_pct"] > 95  # overwhelmingly recurring in this fixture


def test_expense_concentration_ratio():
    account = Account(id=uuid.uuid4(), user_id=uuid.uuid4(), account_number_hash="b" * 64, closing_balance=446500000)
    transactions = _fixture_with_known_recurring_and_variable()

    data = compute_cashflow_analysis(account, transactions)

    # Top 3 payees by outflow: Landlord Co (1,500,000), ATM (20,000), Netflix (15,000) -- dominates total outflow.
    assert data["expense_concentration_ratio_pct"] > 95


def test_by_payment_mode_classification():
    account = Account(id=uuid.uuid4(), user_id=uuid.uuid4(), account_number_hash="c" * 64)
    transactions = _fixture_with_known_recurring_and_variable()

    data = compute_cashflow_analysis(account, transactions)
    by_mode = {m["mode"]: m for m in data["by_payment_mode"]}

    assert by_mode["standing_order"]["occurrence_count"] == 3  # rent
    assert by_mode["cash_withdrawal"]["occurrence_count"] == 1  # ATM
    assert by_mode["pos"]["occurrence_count"] == 1  # supermarket
    assert "unclassified" in by_mode  # Netflix + salary have no mode keyword match


def test_business_vs_personal_classification():
    account = Account(id=uuid.uuid4(), user_id=uuid.uuid4(), account_number_hash="d" * 64)
    transactions = _fixture_with_known_recurring_and_variable()

    data = compute_cashflow_analysis(account, transactions)
    by_category = {c["category"]: c for c in data["business_vs_personal"]}

    assert by_category["business"]["occurrence_count"] == 3  # office rent x3
    assert by_category["personal"]["total_amount"] == 2500000  # netflix (3x5000) + supermarket
    assert "unclassified" in by_category  # ATM withdrawal has no business/personal keyword match
    # Income (salary) must not appear in business_vs_personal at all -- it's outflow-scoped.
    assert sum(c["occurrence_count"] for c in data["business_vs_personal"]) == 8  # 3 rent + 3 netflix + 1 atm + 1 supermarket


def test_cash_buffer_months_present():
    account = Account(id=uuid.uuid4(), user_id=uuid.uuid4(), account_number_hash="e" * 64, closing_balance=446500000)
    transactions = _fixture_with_known_recurring_and_variable()

    data = compute_cashflow_analysis(account, transactions)

    assert data["cash_buffer_months"] is not None


def test_handles_empty_transactions():
    account = Account(id=uuid.uuid4(), user_id=uuid.uuid4(), account_number_hash="f" * 64)
    data = compute_cashflow_analysis(account, [])

    assert data["expense_concentration_ratio_pct"] is None
    assert data["recurring_vs_variable"]["recurring_pct"] is None
    assert data["by_payment_mode"] == []
    assert data["business_vs_personal"] == []
