import uuid
from datetime import date
from decimal import Decimal

from app.models.bank_transactions import BankTransaction, BankTransactionDataSource, TransactionType
from app.services.bank_income_stability import get_income_stability_response


def _make_inflows(monthly_amounts: list[str]) -> list[BankTransaction]:
    return [
        BankTransaction(
            id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            transaction_date=date(2026, month, 1),
            amount=int(float(amount) * 100),
            original_currency="NGN",
            type=TransactionType.credit,
            data_source=BankTransactionDataSource.generic_csv,
        )
        for month, amount in zip(range(1, len(monthly_amounts) + 1), monthly_amounts)
    ]


def test_stable_classification():
    """The task's explicit ask: one test per classification band."""
    transactions = _make_inflows(["100000", "105000", "95000"])
    data, disabled_features = get_income_stability_response(transactions)

    assert data["label"] == "stable"
    assert data["cv_pct"] < 20
    assert disabled_features == []


def test_moderate_classification():
    transactions = _make_inflows(["100000", "130000", "70000"])
    data, disabled_features = get_income_stability_response(transactions)

    assert data["label"] == "moderate"
    assert 20 <= data["cv_pct"] < 40


def test_volatile_classification():
    transactions = _make_inflows(["50000", "150000", "100000"])
    data, disabled_features = get_income_stability_response(transactions)

    assert data["label"] == "volatile"
    assert data["cv_pct"] >= 40


def test_disabled_with_fewer_than_3_months():
    """The task's explicit ask: under-3-months disabled case."""
    transactions = _make_inflows(["100000", "105000"])  # only 2 months

    data, disabled_features = get_income_stability_response(transactions)

    assert data is None
    assert len(disabled_features) == 1
    assert disabled_features[0]["feature_name"] == "income_stability"
