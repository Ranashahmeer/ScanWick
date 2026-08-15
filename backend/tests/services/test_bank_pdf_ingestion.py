import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import select

from app.models.accounts import Account
from app.models.bank_transactions import BankTransaction, BankTransactionDataSource
from app.services.bank_ingestion import extract_canonical_bank_rows
from app.services.bank_pdf_ingestion import (
    ScannedPdfNotSupportedError,
    extract_pdf_text,
    ingest_bank_pdf_bytes,
    parse_bank_statement_text_to_dataframe,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _pdf_bytes() -> bytes:
    return (FIXTURES_DIR / "generic_bank_statement.pdf").read_bytes()


def _scanned_pdf_bytes() -> bytes:
    return (FIXTURES_DIR / "generic_bank_statement_scanned.pdf").read_bytes()


def test_extract_pdf_text_reads_all_five_transaction_lines_in_order():
    text = extract_pdf_text(_pdf_bytes())
    dates_in_order = [line.split()[0] for line in text.splitlines() if line.strip() and line[0].isdigit()]
    assert dates_in_order == ["2026-01-01", "2026-01-05", "2026-01-10", "2026-01-15", "2026-01-20"]


def test_parsed_dataframe_has_five_rows_with_correct_values():
    text = extract_pdf_text(_pdf_bytes())
    df = parse_bank_statement_text_to_dataframe(text)

    assert len(df) == 5
    assert df.iloc[0]["narration"] == "OPENING BALANCE"
    assert df.iloc[2]["debit"] == "184000.00"
    assert df.iloc[2]["narration"] == "POS PURCHASE DANGOTE SUPPLIERS"


def test_pdf_path_produces_identical_canonical_rows_to_the_csv_path():
    """The actual parity assertion the task asks for: same underlying
    transactions, same canonical shape, regardless of source format."""
    pdf_text = extract_pdf_text(_pdf_bytes())
    pdf_df = parse_bank_statement_text_to_dataframe(pdf_text)
    canonical_from_pdf = extract_canonical_bank_rows(pdf_df)

    csv_df = pd.read_csv(FIXTURES_DIR / "generic_bank_sample.csv")
    canonical_from_csv = extract_canonical_bank_rows(csv_df)

    assert len(canonical_from_pdf) == len(canonical_from_csv) == 5
    for pdf_row, csv_row in zip(canonical_from_pdf, canonical_from_csv):
        assert pdf_row == csv_row


def test_scanned_image_only_pdf_is_rejected_not_ocrd():
    """Product decision: this pipeline only reads a PDF's real text layer —
    it never renders pages to images or runs OCR. A scanned/image-only PDF
    (no text layer at all) must fail clearly, not silently produce zero
    rows or attempt image analysis."""
    with pytest.raises(ScannedPdfNotSupportedError):
        extract_pdf_text(_scanned_pdf_bytes())


async def test_ingest_bank_pdf_bytes_writes_account_and_transactions(db_session):
    user_id = uuid.uuid4()

    # Generic fixture PDF — not a real GTBank layout. bank_name is only a
    # label when no dedicated parser matches; pass None so the generic line
    # parser runs (GTBank's dedicated parser would reject this fixture).
    result = await ingest_bank_pdf_bytes(db_session, _pdf_bytes(), user_id, None, upload_id=str(uuid.uuid4()))

    assert result["transactions_created"] == 5
    assert result["rows_rejected"] == 0

    account = (await db_session.execute(select(Account).where(Account.user_id == user_id))).scalar_one()
    assert account.bank_name is None
    assert account.statement_period_start == date(2026, 1, 1)
    assert account.statement_period_end == date(2026, 1, 20)

    transactions = (
        (await db_session.execute(select(BankTransaction).where(BankTransaction.account_id == account.id)))
        .scalars()
        .all()
    )
    assert len(transactions) == 5
    assert all(t.data_source == BankTransactionDataSource.generic_pdf for t in transactions)

    pos_txn = next(t for t in transactions if "POS PURCHASE" in (t.description or ""))
    assert pos_txn.amount == -18400000
