import sqlite3
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.models.accounts import Account
from app.services.encryption import hash_value

RAW_ACCOUNT_NUMBER = "0123456789"


def _make_account(**overrides) -> Account:
    defaults = dict(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        bank_name="GTBank",
        account_number_hash=hash_value(RAW_ACCOUNT_NUMBER),
        base_currency="NGN",
        statement_period_start=date(2026, 1, 1),
        statement_period_end=date(2026, 1, 31),
        opening_balance=420000000,
        closing_balance=1700000000,
    )
    defaults.update(overrides)
    return Account(**defaults)


async def test_create_and_read_account(db_session):
    account = _make_account()
    db_session.add(account)
    await db_session.commit()

    result = await db_session.execute(select(Account).where(Account.id == account.id))
    fetched = result.scalar_one()

    assert fetched.bank_name == "GTBank"
    assert fetched.base_currency == "NGN"
    assert fetched.opening_balance == 420000000
    assert fetched.balance_integrity_passed is None


async def test_account_number_hash_matches_but_is_not_the_plain_number(db_session):
    account = _make_account()
    db_session.add(account)
    await db_session.commit()

    result = await db_session.execute(select(Account).where(Account.id == account.id))
    fetched = result.scalar_one()

    assert fetched.account_number_hash == hash_value(RAW_ACCOUNT_NUMBER)
    assert fetched.account_number_hash != RAW_ACCOUNT_NUMBER
    assert RAW_ACCOUNT_NUMBER not in fetched.account_number_hash


def test_account_number_never_stored_in_plaintext_in_the_database(test_db_path, db_session_factory):
    """Raw-SQL verification (bypassing the ORM entirely), mirroring
    test_bank_account_encryption.py's pattern: the raw account number must
    not be a substring of anything actually persisted to disk."""
    import asyncio

    async def _insert():
        async with db_session_factory() as session:
            session.add(_make_account())
            await session.commit()

    asyncio.run(_insert())

    conn = sqlite3.connect(test_db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM accounts")
        columns = [d[0] for d in cur.description]
        rows = cur.fetchall()
    finally:
        conn.close()

    assert len(rows) == 1
    for row in rows:
        for col_name, value in zip(columns, row):
            assert RAW_ACCOUNT_NUMBER not in str(value), f"plaintext leaked into column {col_name!r}"


async def test_balance_integrity_fields(db_session):
    account = _make_account(
        opening_balance=100000,
        closing_balance=150000,
        computed_closing_balance=135000,
        balance_integrity_passed=False,
        balance_discrepancy=15000,
    )
    db_session.add(account)
    await db_session.commit()

    result = await db_session.execute(select(Account).where(Account.id == account.id))
    fetched = result.scalar_one()
    assert fetched.balance_integrity_passed is False
    assert fetched.balance_discrepancy == 15000


async def test_update_account(db_session):
    account = _make_account()
    db_session.add(account)
    await db_session.commit()

    account.closing_balance = 2000000000
    await db_session.commit()

    result = await db_session.execute(select(Account).where(Account.id == account.id))
    assert result.scalar_one().closing_balance == 2000000000


async def test_delete_account(db_session):
    account = _make_account()
    db_session.add(account)
    await db_session.commit()

    await db_session.delete(account)
    await db_session.commit()

    result = await db_session.execute(select(Account).where(Account.id == account.id))
    assert result.scalar_one_or_none() is None
