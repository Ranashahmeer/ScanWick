import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy import select

from app.models.accounts import Account
from app.models.bank_transactions import BankTransaction, BankTransactionDataSource, TransactionType
from app.models.uploads import Upload
from app.services.bank_ingestion import compute_bank_quality_report, extract_canonical_bank_rows, ingest_bank_dataframe
from app.services.encryption import hash_value

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
RAW_ACCOUNT_NUMBER = "1234567890"


def _load(name: str) -> pd.DataFrame:
    return pd.read_csv(FIXTURES_DIR / name)


def test_extract_canonical_rows_shape():
    rows = extract_canonical_bank_rows(_load("generic_bank_sample.csv"))

    assert len(rows) == 5

    opening = rows[0]
    assert opening["transaction_date"] == date(2026, 1, 1)
    assert opening["amount"] == 100000000
    assert opening["type"] == TransactionType.credit
    assert opening["balance_after"] == 100000000
    assert opening["payee_normalized"] == "Opening Balance"

    inward = rows[1]
    assert inward["amount"] == 240000000
    assert inward["type"] == TransactionType.credit

    pos_purchase = rows[2]
    assert pos_purchase["amount"] == -18400000
    assert pos_purchase["type"] == TransactionType.debit
    assert pos_purchase["balance_after"] == 321600000
    assert pos_purchase["payee_normalized"] == "Pos Purchase Dangote Suppliers"

    atm = rows[3]
    assert atm["amount"] == -5000000
    assert atm["type"] == TransactionType.debit

    charge = rows[4]
    assert charge["amount"] == -150000
    assert charge["original_currency"] == "NGN"


async def test_ingestion_writes_account_and_transactions(db_session):
    user_id = uuid.uuid4()
    df = _load("generic_bank_sample.csv")

    result = await ingest_bank_dataframe(
        db_session, df, user_id, "GTBank", BankTransactionDataSource.generic_csv, upload_id=str(uuid.uuid4())
    )

    assert result["transactions_created"] == 5
    assert result["rows_rejected"] == 0

    account = (await db_session.execute(select(Account).where(Account.user_id == user_id))).scalar_one()
    assert account.bank_name == "GTBank"
    assert account.statement_period_start == date(2026, 1, 1)
    assert account.statement_period_end == date(2026, 1, 20)

    transactions = (
        (await db_session.execute(select(BankTransaction).where(BankTransaction.account_id == account.id)))
        .scalars()
        .all()
    )
    assert len(transactions) == 5
    assert all(t.data_source == BankTransactionDataSource.generic_csv for t in transactions)


async def test_account_number_hash_resolved_from_csv_column_not_plaintext(db_session):
    user_id = uuid.uuid4()
    df = _load("generic_bank_sample.csv")

    await ingest_bank_dataframe(
        db_session, df, user_id, "GTBank", BankTransactionDataSource.generic_csv, upload_id=str(uuid.uuid4())
    )

    account = (await db_session.execute(select(Account).where(Account.user_id == user_id))).scalar_one()
    assert account.account_number_hash == hash_value(RAW_ACCOUNT_NUMBER)
    assert RAW_ACCOUNT_NUMBER not in account.account_number_hash


async def test_account_number_falls_back_to_upload_id_hash_when_no_column_present(db_session):
    user_id = uuid.uuid4()
    upload_id = str(uuid.uuid4())
    df = pd.DataFrame(
        [
            {"date": "2026-01-01", "narration": "Test", "debit": 0, "credit": 1000, "balance": 1000},
        ]
    )

    result = await ingest_bank_dataframe(
        db_session, df, user_id, None, BankTransactionDataSource.generic_csv, upload_id=upload_id
    )

    assert result["transactions_created"] == 1
    account = (await db_session.execute(select(Account).where(Account.user_id == user_id))).scalar_one()
    assert account.account_number_hash == hash_value(f"unknown-account:{upload_id}")


async def test_rows_missing_date_or_amount_are_rejected_not_crashed_on(db_session):
    user_id = uuid.uuid4()
    df = pd.DataFrame(
        [
            {"date": "2026-01-01", "narration": "Good row", "debit": 0, "credit": 1000},
            {"date": None, "narration": "Missing date", "debit": 0, "credit": 500},
        ]
    )

    result = await ingest_bank_dataframe(
        db_session, df, user_id, None, BankTransactionDataSource.generic_csv, upload_id=str(uuid.uuid4())
    )

    assert result["transactions_created"] == 1
    assert result["rows_rejected"] == 1


def test_extract_canonical_bank_rows_rejects_ambiguous_date_with_no_confirmed_locale():
    """3.7: "03/04/2026" is genuinely ambiguous (3 April vs March 4) --
    with no date_locale confirmed for this mapping, the row must not
    silently guess a date. transaction_date comes back None (so the row is
    rejected downstream, same as any other missing-required-field row) and
    the row carries a named AMBIGUOUS_DATE warning."""
    df = pd.DataFrame(
        [{"date": "03/04/2026", "narration": "Ambiguous", "debit": 0, "credit": 1000, "balance": 1000}]
    )
    rows = extract_canonical_bank_rows(df)

    assert rows[0]["transaction_date"] is None
    assert rows[0]["_row_warning"]["code"] == "AMBIGUOUS_DATE"
    assert rows[0]["_row_warning"]["row"] == 0
    assert rows[0]["_row_warning"]["field"] == "transaction_date"


def test_extract_canonical_bank_rows_resolves_ambiguous_date_once_locale_confirmed():
    df = pd.DataFrame(
        [{"date": "03/04/2026", "narration": "Ambiguous", "debit": 0, "credit": 1000, "balance": 1000}]
    )
    rows = extract_canonical_bank_rows(df, value_rules={"date_locale": "month_first"})

    assert rows[0]["transaction_date"] == date(2026, 3, 4)
    assert rows[0]["_row_warning"] is None


async def test_ingest_bank_dataframe_surfaces_ambiguous_date_as_a_named_rejected_row(db_session):
    """End-to-end: the quality report's `rejected_rows` must name exactly
    why an ambiguous-date row didn't land as a transaction, with a row
    reference and the raw value -- not just a lower transactions_created
    count."""
    user_id = uuid.uuid4()
    df = pd.DataFrame(
        [
            {"date": "2026-01-01", "narration": "Good row", "debit": 0, "credit": 1000, "balance": 1000},
            {"date": "03/04/2026", "narration": "Ambiguous date", "debit": 0, "credit": 500, "balance": 1500},
        ]
    )

    result = await ingest_bank_dataframe(
        db_session, df, user_id, None, BankTransactionDataSource.generic_csv, upload_id=str(uuid.uuid4())
    )

    assert result["transactions_created"] == 1
    assert result["quality_report"]["rows_rejected"] == 1
    rejected = result["quality_report"]["rejected_rows"]
    assert len(rejected) == 1
    assert rejected[0]["code"] == "AMBIGUOUS_DATE"
    assert rejected[0]["row"] == 1
    assert rejected[0]["field"] == "transaction_date"
    assert rejected[0]["raw_value"] == "03/04/2026"


async def test_ingest_bank_dataframe_confirmed_locale_resolves_the_ambiguous_row(db_session):
    user_id = uuid.uuid4()
    df = pd.DataFrame(
        [{"date": "03/04/2026", "narration": "Ambiguous date", "debit": 0, "credit": 500, "balance": 500}]
    )

    result = await ingest_bank_dataframe(
        db_session, df, user_id, None, BankTransactionDataSource.generic_csv, upload_id=str(uuid.uuid4()),
        value_rules={"date_locale": "day_first"},
    )

    assert result["transactions_created"] == 1
    assert result["quality_report"]["rows_rejected"] == 0
    assert result["quality_report"]["rejected_rows"] == []


def test_compute_bank_quality_report_shape_and_months_of_data():
    rows = extract_canonical_bank_rows(_load("generic_bank_sample.csv"))
    integrity = {
        "opening_balance": 100000000,
        "closing_balance": 316450000,
        "computed_closing_balance": 316450000,
        "balance_integrity_passed": True,
        "balance_discrepancy": None,
    }

    report = compute_bank_quality_report(rows, integrity)

    assert report["transactions_parsed"] == 5
    assert report["rows_rejected"] == 0
    assert report["date_range_start"] == date(2026, 1, 1)
    assert report["date_range_end"] == date(2026, 1, 20)
    # All 5 rows fall in January 2026 -- one distinct calendar month.
    assert report["months_of_data"] == 1
    assert report["balance_integrity"] == integrity
    assert report["warnings"] == []


def test_compute_bank_quality_report_flags_date_gap_over_threshold():
    rows = [
        {"transaction_date": date(2026, 1, 1), "amount": 10000},
        # 10-day silence -- exceeds the 7-day GAP_THRESHOLD_DAYS.
        {"transaction_date": date(2026, 1, 11), "amount": 10000},
    ]
    integrity = {
        "opening_balance": None,
        "closing_balance": None,
        "computed_closing_balance": None,
        "balance_integrity_passed": None,
        "balance_discrepancy": None,
    }

    report = compute_bank_quality_report(rows, integrity)

    assert report["date_gaps"] == [{"gap_start": "2026-01-02", "gap_end": "2026-01-10", "days": 9}]


def test_compute_bank_quality_report_warns_on_rejected_rows_and_failed_integrity():
    rows = [
        {"transaction_date": date(2026, 1, 1), "amount": 10000},
        {"transaction_date": None, "amount": 5000},
    ]
    integrity = {
        "opening_balance": 0,
        "closing_balance": 100000,
        "computed_closing_balance": 10000,
        "balance_integrity_passed": False,
        "balance_discrepancy": 90000,
    }

    report = compute_bank_quality_report(rows, integrity)

    assert report["rows_rejected"] == 1
    fields_warned = {w["field"] for w in report["warnings"]}
    assert fields_warned == {"transaction_date/amount", "balance_integrity"}
    # 3.7: a row with no _row_warning (plain dicts here, not built via
    # extract_canonical_bank_rows) still gets a synthesized, row-referenced
    # named warning -- no rejected row is ever unaccounted for.
    assert len(report["rejected_rows"]) == 1
    assert report["rejected_rows"][0] == {
        "row": 1,
        "field": "transaction_date",
        "code": "MISSING_REQUIRED_FIELD",
        "message": "Row 1 could not be resolved: missing transaction_date.",
        "raw_value": None,
        "remediation": "Confirm the column mapping for this field and re-upload.",
    }


async def test_ingestion_writes_upload_row_with_bank_quality_metadata(db_session):
    user_id = uuid.uuid4()
    upload_id = str(uuid.uuid4())
    df = _load("generic_bank_sample.csv")

    await ingest_bank_dataframe(
        db_session, df, user_id, "GTBank", BankTransactionDataSource.generic_csv, upload_id=upload_id
    )

    upload = (await db_session.execute(select(Upload).where(Upload.id == uuid.UUID(upload_id)))).scalar_one()
    assert upload.rows_parsed == 5
    assert upload.rows_rejected == 0
    assert upload.date_range_start == date(2026, 1, 1)
    assert upload.date_range_end == date(2026, 1, 20)
    assert upload.analyzer_metadata["months_of_data"] == 1
    assert upload.analyzer_metadata["balance_integrity"]["balance_integrity_passed"] is True
    assert upload.analyzer_metadata["date_gaps"] == []


def test_credit_column_not_shadowed_by_a_narration_column_containing_cr():
    """Regression test: a 'description' narration column contains the
    substring 'cr' ("des-CR-iption"), which used to make find_column()
    misdetect it as the credit column ahead of the real 'credit' column
    (both scanwick_bank_savings_clean.csv and scanwick_bank_wallet_clean.csv
    hit this in production data -- every credit-side transaction in both
    files was silently zeroed). _CREDIT_KEYWORDS no longer includes the bare
    'cr' token, so this must resolve to the real 'credit' column."""
    df = pd.DataFrame(
        [
            {"date": "2026-01-01", "description": "Inward transfer", "debit": 0, "credit": 500000, "balance": 500000},
            {"date": "2026-01-02", "description": "POS purchase", "debit": 20000, "credit": 0, "balance": 480000},
        ]
    )
    rows = extract_canonical_bank_rows(df)
    assert rows[0]["type"] == TransactionType.credit
    assert rows[0]["amount"] == 50000000  # not 0
    assert rows[1]["type"] == TransactionType.debit
    assert rows[1]["amount"] == -2000000


async def test_mono_ingestion_upload_id_does_not_crash_and_writes_no_upload_row(db_session):
    """Mono passes its own mono_account_id (not a UUID) as upload_id -- must
    not crash trying to persist an Upload row for it."""
    user_id = uuid.uuid4()
    df = _load("generic_bank_sample.csv")

    result = await ingest_bank_dataframe(
        db_session, df, user_id, "GTBank", BankTransactionDataSource.mono_api, upload_id="acc_not_a_uuid"
    )

    assert result["transactions_created"] == 5
    uploads = (await db_session.execute(select(Upload))).scalars().all()
    assert uploads == []


async def test_reingesting_the_same_statement_reuses_the_account_and_skips_duplicate_transactions(db_session):
    """Audit #14 regression: re-uploading the same statement (or a client
    retry) used to create a brand-new Account every time and blindly
    re-insert every transaction, silently doubling every downstream
    financial figure. A second ingestion of the identical file for the same
    user must reuse the existing Account and skip every transaction as a
    duplicate."""
    user_id = uuid.uuid4()
    df = _load("generic_bank_sample.csv")

    first = await ingest_bank_dataframe(
        db_session, df, user_id, "GTBank", BankTransactionDataSource.generic_csv, upload_id=str(uuid.uuid4())
    )
    second = await ingest_bank_dataframe(
        db_session, df, user_id, "GTBank", BankTransactionDataSource.generic_csv, upload_id=str(uuid.uuid4())
    )

    assert first["transactions_created"] == 5
    assert second["transactions_created"] == 0
    assert second["duplicates_skipped"] == 5
    assert first["account_id"] == second["account_id"]

    accounts = (await db_session.execute(select(Account).where(Account.user_id == user_id))).scalars().all()
    assert len(accounts) == 1
    transactions = (
        (await db_session.execute(select(BankTransaction).where(BankTransaction.account_id == accounts[0].id)))
        .scalars()
        .all()
    )
    assert len(transactions) == 5


async def test_ingesting_a_genuinely_different_statement_for_the_same_account_extends_transactions(db_session):
    """The dedup check must not falsely suppress genuinely new transactions
    on a real second statement for the same account (extends coverage, not
    a duplicate)."""
    user_id = uuid.uuid4()
    df = _load("generic_bank_sample.csv")
    await ingest_bank_dataframe(
        db_session, df, user_id, "GTBank", BankTransactionDataSource.generic_csv, upload_id=str(uuid.uuid4())
    )

    new_month_df = df.copy()
    new_month_df["date"] = ["2026-02-01", "2026-02-05", "2026-02-10", "2026-02-15", "2026-02-20"]
    second = await ingest_bank_dataframe(
        db_session, new_month_df, user_id, "GTBank", BankTransactionDataSource.generic_csv, upload_id=str(uuid.uuid4())
    )

    assert second["transactions_created"] == 5
    assert second["duplicates_skipped"] == 0

    accounts = (await db_session.execute(select(Account).where(Account.user_id == user_id))).scalars().all()
    assert len(accounts) == 1
    assert accounts[0].statement_period_start == date(2026, 1, 1)
    assert accounts[0].statement_period_end == date(2026, 2, 20)
