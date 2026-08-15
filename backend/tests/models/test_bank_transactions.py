import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.models.accounts import Account
from app.models.bank_transactions import (
    BankTransaction,
    BankTransactionDataSource,
    TransactionCategory,
    TransactionMode,
    TransactionType,
)
from app.services.encryption import hash_value


async def _make_account(db_session) -> Account:
    account = Account(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        bank_name="Access Bank",
        account_number_hash=hash_value("9876543210"),
        base_currency="NGN",
    )
    db_session.add(account)
    await db_session.commit()
    return account


def _make_transaction(account_id, **overrides) -> BankTransaction:
    defaults = dict(
        id=uuid.uuid4(),
        account_id=account_id,
        transaction_date=date(2026, 1, 5),
        description="POS PURCHASE DANGOTE SUPPLIERS",
        amount=-1840000,
        original_currency="NGN",
        type=TransactionType.debit,
        data_source=BankTransactionDataSource.access_csv,
    )
    defaults.update(overrides)
    return BankTransaction(**defaults)


async def test_create_and_read_bank_transaction(db_session):
    account = await _make_account(db_session)
    txn = _make_transaction(account.id)
    db_session.add(txn)
    await db_session.commit()

    result = await db_session.execute(select(BankTransaction).where(BankTransaction.id == txn.id))
    fetched = result.scalar_one()

    assert fetched.account_id == account.id
    assert fetched.amount == -1840000
    assert fetched.type == TransactionType.debit
    assert fetched.data_source == BankTransactionDataSource.access_csv


async def test_defaults_for_is_recurring_is_own_account_transfer_is_anomalous(db_session):
    account = await _make_account(db_session)
    txn = _make_transaction(account.id)
    db_session.add(txn)
    await db_session.commit()

    result = await db_session.execute(select(BankTransaction).where(BankTransaction.id == txn.id))
    fetched = result.scalar_one()
    assert fetched.is_recurring is False
    assert fetched.is_own_account_transfer is False
    assert fetched.is_anomalous is False
    assert fetched.category == TransactionCategory.unknown


async def test_credit_transaction_with_mode_and_category(db_session):
    account = await _make_account(db_session)
    txn = _make_transaction(
        account.id,
        amount=2400000000,
        type=TransactionType.credit,
        mode=TransactionMode.bank_transfer,
        category=TransactionCategory.income,
        description="INWARD TRANSFER TECHCO NIGERIA LTD",
        payee_normalized="TechCo Nigeria Ltd",
        balance_after=4140000000,
    )
    db_session.add(txn)
    await db_session.commit()

    result = await db_session.execute(select(BankTransaction).where(BankTransaction.id == txn.id))
    fetched = result.scalar_one()
    assert fetched.mode == TransactionMode.bank_transfer
    assert fetched.category == TransactionCategory.income
    assert fetched.payee_normalized == "TechCo Nigeria Ltd"
    assert fetched.balance_after == 4140000000


async def test_fraud_flags_stored_as_json(db_session):
    account = await _make_account(db_session)
    flags = [{"flag_type": "z_score_anomaly", "severity": "low", "z_score": 3.2}]
    txn = _make_transaction(account.id, fraud_flags=flags)
    db_session.add(txn)
    await db_session.commit()

    result = await db_session.execute(select(BankTransaction).where(BankTransaction.id == txn.id))
    assert result.scalar_one().fraud_flags == flags


async def test_each_data_source_enum_value_is_storable(db_session):
    account = await _make_account(db_session)
    for source in BankTransactionDataSource:
        db_session.add(_make_transaction(account.id, id=uuid.uuid4(), data_source=source))
    await db_session.commit()

    result = await db_session.execute(
        select(BankTransaction.data_source).where(BankTransaction.account_id == account.id)
    )
    assert {row[0] for row in result.all()} == set(BankTransactionDataSource)


async def test_update_bank_transaction(db_session):
    account = await _make_account(db_session)
    txn = _make_transaction(account.id)
    db_session.add(txn)
    await db_session.commit()

    txn.is_own_account_transfer = True
    await db_session.commit()

    result = await db_session.execute(select(BankTransaction).where(BankTransaction.id == txn.id))
    assert result.scalar_one().is_own_account_transfer is True


async def test_delete_bank_transaction(db_session):
    account = await _make_account(db_session)
    txn = _make_transaction(account.id)
    db_session.add(txn)
    await db_session.commit()

    await db_session.delete(txn)
    await db_session.commit()

    result = await db_session.execute(select(BankTransaction).where(BankTransaction.id == txn.id))
    assert result.scalar_one_or_none() is None
