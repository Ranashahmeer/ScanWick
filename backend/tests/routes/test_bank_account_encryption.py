import asyncio
import sqlite3

from sqlalchemy import select

from app.models import BankAccountIdentifier
from app.services.encryption import decrypt_field, hash_value

RAW_ACCOUNT_NUMBER = "1234567890123456"

_CSV_BYTES = (
    b"date,narration,debit,credit,balance,account_number\n"
    b"2026-01-01,Opening Balance,0,1000,1000," + RAW_ACCOUNT_NUMBER.encode() + b"\n"
    b"2026-01-05,ATM Withdrawal,200,0,800," + RAW_ACCOUNT_NUMBER.encode() + b"\n"
)


def test_bank_account_number_never_stored_in_plaintext(
    authenticated_client, db_session_factory, test_db_path
):
    """Uploading a bank statement should persist a hash + encrypted copy of
    the account number, round-trip correctly via decrypt_field, and never
    leave the raw account number recoverable from a direct DB query."""
    response = authenticated_client.post(
        "/api/analyze",
        files={"file": ("statement.csv", _CSV_BYTES, "text/csv")},
    )
    assert response.status_code == 200
    assert response.json().get("dataset_type") == "bank_statement"

    rows = asyncio.run(_fetch_rows(db_session_factory))
    assert len(rows) == 1, "expected exactly one persisted bank account identifier"
    row = rows[0]

    # round-trip via the application's own decrypt_field
    assert decrypt_field(row.account_number_encrypted) == RAW_ACCOUNT_NUMBER
    assert row.account_number_hash == hash_value(RAW_ACCOUNT_NUMBER)

    # query the DB directly (raw sqlite3, bypassing the ORM entirely) —
    # the raw account number must not be a substring of anything stored
    conn = sqlite3.connect(test_db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT account_number_hash, account_number_encrypted FROM bank_account_identifiers")
        db_rows = cur.fetchall()
    finally:
        conn.close()

    assert len(db_rows) == 1
    for hash_col, encrypted_col in db_rows:
        assert RAW_ACCOUNT_NUMBER not in hash_col
        assert RAW_ACCOUNT_NUMBER not in encrypted_col


async def _fetch_rows(session_factory):
    async with session_factory() as session:
        result = await session.execute(select(BankAccountIdentifier))
        return result.scalars().all()
