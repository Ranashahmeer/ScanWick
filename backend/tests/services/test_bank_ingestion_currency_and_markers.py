import datetime
import uuid
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy import select

from app.models.accounts import Account
from app.models.bank_transactions import BankTransaction, BankTransactionDataSource
from app.models.contextual_markers import ContextualMarker
from app.models.reconciliation_reports import AnalyzerType
from app.services.bank_ingestion import ingest_bank_dataframe
from app.services.contextual_markers import create_contextual_marker
from app.services.exchange_rates import upsert_exchange_rate

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> pd.DataFrame:
    df = pd.read_csv(FIXTURES_DIR / name)
    return df


async def test_ingestion_converts_using_transaction_date_rate_not_latest(db_session):
    user_id = uuid.uuid4()
    df = _load("generic_bank_sample.csv")
    df["currency"] = "USD"  # force a real conversion instead of the NGN no-op case

    # Three rates at different dates; the fixture's rows are dated 2026-01-01
    # through 2026-01-20, so they must all use the 2026-01-01 rate (the latest
    # one on or before each row's date), never the later 2026-06-01 rate.
    await upsert_exchange_rate(db_session, "USD", "NGN", datetime.date(2025, 12, 1), 140000)
    await upsert_exchange_rate(db_session, "USD", "NGN", datetime.date(2026, 1, 1), 150000)
    await upsert_exchange_rate(db_session, "USD", "NGN", datetime.date(2026, 6, 1), 170000)

    await ingest_bank_dataframe(
        db_session, df, user_id, "GTBank", BankTransactionDataSource.generic_csv, upload_id=str(uuid.uuid4())
    )

    account = (await db_session.execute(select(Account).where(Account.user_id == user_id))).scalar_one()
    transactions = (
        (await db_session.execute(select(BankTransaction).where(BankTransaction.account_id == account.id)))
        .scalars()
        .all()
    )
    assert len(transactions) == 5
    for txn in transactions:
        assert txn.exchange_rate == 150000
        assert txn.base_currency_amount == txn.amount * 150000


async def test_ingestion_leaves_conversion_null_when_no_rate_known(db_session):
    user_id = uuid.uuid4()
    df = _load("generic_bank_sample.csv")
    df["currency"] = "USD"

    await ingest_bank_dataframe(
        db_session, df, user_id, "GTBank", BankTransactionDataSource.generic_csv, upload_id=str(uuid.uuid4())
    )

    account = (await db_session.execute(select(Account).where(Account.user_id == user_id))).scalar_one()
    transactions = (
        (await db_session.execute(select(BankTransaction).where(BankTransaction.account_id == account.id)))
        .scalars()
        .all()
    )
    assert all(t.exchange_rate is None for t in transactions)
    assert all(t.base_currency_amount is None for t in transactions)


async def test_ingestion_defaults_to_rate_1_when_currency_matches_base_currency(db_session):
    user_id = uuid.uuid4()
    df = _load("generic_bank_sample.csv")  # NGN rows, base_currency defaults to NGN too

    await ingest_bank_dataframe(
        db_session, df, user_id, "GTBank", BankTransactionDataSource.generic_csv, upload_id=str(uuid.uuid4())
    )

    account = (await db_session.execute(select(Account).where(Account.user_id == user_id))).scalar_one()
    transactions = (
        (await db_session.execute(select(BankTransaction).where(BankTransaction.account_id == account.id)))
        .scalars()
        .all()
    )
    assert len(transactions) == 5
    for txn in transactions:
        assert txn.exchange_rate == 100
        assert txn.base_currency_amount == txn.amount


async def test_ingestion_flags_transactions_inside_existing_marker_at_write_time(db_session):
    user_id = uuid.uuid4()
    db_session.add(
        ContextualMarker(
            id=uuid.uuid4(),
            merchant_id=user_id,
            analyzer_type=AnalyzerType.bank,
            label="Fraud Investigation Window",
            start_date=datetime.date(2026, 1, 5),
            end_date=datetime.date(2026, 1, 15),
        )
    )
    await db_session.commit()

    df = _load("generic_bank_sample.csv")
    await ingest_bank_dataframe(
        db_session, df, user_id, "GTBank", BankTransactionDataSource.generic_csv, upload_id=str(uuid.uuid4())
    )

    account = (await db_session.execute(select(Account).where(Account.user_id == user_id))).scalar_one()
    transactions = (
        (await db_session.execute(select(BankTransaction).where(BankTransaction.account_id == account.id)))
        .scalars()
        .all()
    )
    by_date = {t.transaction_date: t for t in transactions}
    assert by_date[datetime.date(2026, 1, 1)].is_anomalous is False  # before
    assert by_date[datetime.date(2026, 1, 5)].is_anomalous is True  # boundary start
    assert by_date[datetime.date(2026, 1, 10)].is_anomalous is True  # inside
    assert by_date[datetime.date(2026, 1, 15)].is_anomalous is True  # boundary end
    assert by_date[datetime.date(2026, 1, 20)].is_anomalous is False  # after


async def test_new_marker_retroactively_reflags_existing_bank_transactions(db_session):
    user_id = uuid.uuid4()
    df = _load("generic_bank_sample.csv")
    await ingest_bank_dataframe(
        db_session, df, user_id, "GTBank", BankTransactionDataSource.generic_csv, upload_id=str(uuid.uuid4())
    )

    account = (await db_session.execute(select(Account).where(Account.user_id == user_id))).scalar_one()
    transactions_before = (
        (await db_session.execute(select(BankTransaction).where(BankTransaction.account_id == account.id)))
        .scalars()
        .all()
    )
    assert all(t.is_anomalous is False for t in transactions_before)

    # Marker created *after* ingestion — the retroactive reflag job (task
    # 1.25) must flip existing rows in range, not just future ingestion.
    await create_contextual_marker(
        db_session,
        merchant_id=user_id,
        analyzer_type=AnalyzerType.bank,
        label="Retroactive Marker",
        start_date=datetime.date(2026, 1, 10),
        end_date=datetime.date(2026, 1, 15),
    )

    transactions_after = (
        (await db_session.execute(select(BankTransaction).where(BankTransaction.account_id == account.id)))
        .scalars()
        .all()
    )
    by_date = {t.transaction_date: t for t in transactions_after}
    assert by_date[datetime.date(2026, 1, 5)].is_anomalous is False
    assert by_date[datetime.date(2026, 1, 10)].is_anomalous is True
    assert by_date[datetime.date(2026, 1, 15)].is_anomalous is True
    assert by_date[datetime.date(2026, 1, 20)].is_anomalous is False


async def test_retroactive_reflag_scoped_to_the_markers_own_merchant_only(db_session):
    """A marker created for one user must not flag another user's bank
    transactions, even if their dates overlap — reflag_bank_transactions_for_marker
    scopes through accounts.user_id, this proves that scoping actually holds."""
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    df = _load("generic_bank_sample.csv")
    await ingest_bank_dataframe(
        db_session, df, user_a, "GTBank", BankTransactionDataSource.generic_csv, upload_id=str(uuid.uuid4())
    )
    await ingest_bank_dataframe(
        db_session, df, user_b, "Access Bank", BankTransactionDataSource.generic_csv, upload_id=str(uuid.uuid4())
    )

    await create_contextual_marker(
        db_session,
        merchant_id=user_a,
        analyzer_type=AnalyzerType.bank,
        label="User A Only",
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 1, 31),
    )

    account_a = (await db_session.execute(select(Account).where(Account.user_id == user_a))).scalar_one()
    account_b = (await db_session.execute(select(Account).where(Account.user_id == user_b))).scalar_one()
    txns_a = (
        (await db_session.execute(select(BankTransaction).where(BankTransaction.account_id == account_a.id)))
        .scalars()
        .all()
    )
    txns_b = (
        (await db_session.execute(select(BankTransaction).where(BankTransaction.account_id == account_b.id)))
        .scalars()
        .all()
    )
    assert all(t.is_anomalous is True for t in txns_a)
    assert all(t.is_anomalous is False for t in txns_b)
