import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from app.models.accounts import Account
from app.models.bank_transactions import BankTransaction, BankTransactionDataSource
from app.services.bank_ingestion import extract_canonical_bank_rows
from app.services.encryption import hash_value
from app.services.mono_ingestion import ingest_mono_account, mono_transactions_to_dataframe

NIGERIA_ACCOUNT_DETAILS = {
    "id": "acc_ng_1",
    "accountNumber": "1234567890",
    "currency": "NGN",
    "institution": {"name": "GTBank", "bankCode": "058"},
}

NIGERIA_TRANSACTIONS = [
    {"id": "t1", "date": "2026-01-01T00:00:00.000Z", "narration": "Opening Balance", "amount": 100000000, "type": "credit", "balance": 100000000},
    {"id": "t2", "date": "2026-01-05T00:00:00.000Z", "narration": "Inward Transfer Techco", "amount": 240000000, "type": "credit", "balance": 340000000},
    {"id": "t3", "date": "2026-01-10T00:00:00.000Z", "narration": "POS Purchase Dangote", "amount": 18400000, "type": "debit", "balance": 321600000},
]

GHANA_ACCOUNT_DETAILS = {
    "id": "acc_gh_1",
    "accountNumber": "0987654321",
    "currency": "GHS",
    "institution": {"name": "GCB Bank", "bankCode": "GH030100"},
}

GHANA_TRANSACTIONS = [
    {"id": "g1", "date": "2026-02-01T00:00:00.000Z", "narration": "Salary Payment", "amount": 500000, "type": "credit", "balance": 500000},
]


def test_mono_transactions_to_dataframe_converts_minor_to_major_and_direction():
    df = mono_transactions_to_dataframe(NIGERIA_TRANSACTIONS)

    assert len(df) == 3
    assert df.iloc[0]["credit"] == 100000000
    assert df.iloc[0]["debit"] is None
    assert df.iloc[2]["debit"] == 18400000
    assert df.iloc[2]["credit"] is None
    assert df.iloc[2]["balance"] == 321600000


def test_mono_dataframe_feeds_the_same_canonical_extraction_as_csv_and_pdf():
    df = mono_transactions_to_dataframe(NIGERIA_TRANSACTIONS)
    canonical_rows = extract_canonical_bank_rows(df)

    assert canonical_rows[0]["amount"] == 100000000
    assert canonical_rows[2]["amount"] == -18400000
    assert canonical_rows[2]["payee_normalized"] == "Pos Purchase Dangote"


async def test_ingest_mono_account_nigeria_end_to_end(db_session):
    user_id = uuid.uuid4()

    with (
        patch("app.services.mono_ingestion.fetch_account_details", new=AsyncMock(return_value=NIGERIA_ACCOUNT_DETAILS)),
        patch(
            "app.services.mono_ingestion.fetch_all_account_transactions",
            new=AsyncMock(return_value=NIGERIA_TRANSACTIONS),
        ),
    ):
        result = await ingest_mono_account(db_session, user_id, "acc_ng_1")

    assert result["transactions_created"] == 3
    assert result["rows_rejected"] == 0

    account = (await db_session.execute(select(Account).where(Account.user_id == user_id))).scalar_one()
    assert account.bank_name == "GTBank"
    assert account.base_currency == "NGN"
    assert account.account_number_hash == hash_value("1234567890")

    transactions = (
        (await db_session.execute(select(BankTransaction).where(BankTransaction.account_id == account.id)))
        .scalars()
        .all()
    )
    assert len(transactions) == 3
    assert all(t.data_source == BankTransactionDataSource.mono_api for t in transactions)


async def test_ingest_mono_account_ghana_uses_returned_currency_and_bank(db_session):
    """Same code path as the Nigeria test above — no per-country branching
    anywhere in mono_ingestion.py — just different data returned by Mono."""
    user_id = uuid.uuid4()

    with (
        patch("app.services.mono_ingestion.fetch_account_details", new=AsyncMock(return_value=GHANA_ACCOUNT_DETAILS)),
        patch(
            "app.services.mono_ingestion.fetch_all_account_transactions",
            new=AsyncMock(return_value=GHANA_TRANSACTIONS),
        ),
    ):
        result = await ingest_mono_account(db_session, user_id, "acc_gh_1")

    assert result["transactions_created"] == 1

    account = (await db_session.execute(select(Account).where(Account.user_id == user_id))).scalar_one()
    assert account.bank_name == "GCB Bank"
    assert account.base_currency == "GHS"
    assert account.account_number_hash == hash_value("0987654321")


async def test_ingest_mono_account_falls_back_to_placeholder_hash_when_no_account_number(db_session):
    user_id = uuid.uuid4()
    details_without_number = {"currency": "KES", "institution": {"name": "Equity Bank"}}

    with (
        patch("app.services.mono_ingestion.fetch_account_details", new=AsyncMock(return_value=details_without_number)),
        patch("app.services.mono_ingestion.fetch_all_account_transactions", new=AsyncMock(return_value=[])),
    ):
        await ingest_mono_account(db_session, user_id, "acc_ke_1")

    account = (await db_session.execute(select(Account).where(Account.user_id == user_id))).scalar_one()
    assert account.account_number_hash == hash_value("unknown-mono-account:acc_ke_1")
    assert account.base_currency == "KES"
