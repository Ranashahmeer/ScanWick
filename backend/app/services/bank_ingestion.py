import asyncio
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery_app
from app.database import async_session
from app.models.accounts import Account
from app.models.bank_transactions import BankTransaction, BankTransactionDataSource, TransactionType
from app.models.reconciliation_reports import AnalyzerType
from app.models.uploads import Upload, UploadStatus
from app.services.bank_account_integrity import compute_balance_integrity_for_rows
from app.services.column_mapping import summarize_mapping_applied
from app.services.contextual_markers import get_marker_ranges, is_within_marker_ranges
from app.services.encryption import hash_value
from app.services.exchange_rates import get_historical_rate
from app.services.upload_staging import (
    delete_staged_upload,
    mark_upload_failed,
    read_staged_upload,
)
from app.utils.numeric import parse_kobo as _kobo_or_none
from app.utils.analyzer import COLUMN_CANDIDATES, find_column
from app.utils.locale_dates import parse_locale_date

# A week of total silence on an otherwise-active account is unusual enough to
# surface in the quality report (task 1.26) — not proof of a parsing bug by
# itself, just a reasonable, documented default rather than an implicit one.
GAP_THRESHOLD_DAYS = 7

# Same keyword lists the existing bank-statement industry analyzer
# (_analyze_bank_statement in this module) already uses for credit/debit/
# balance/narration detection, and the same ones /api/analyze's
# _find_account_number_column uses for the account-number column. Reused
# here via the existing, already-public find_column() rather than
# duplicating the matching algorithm. _analyze_bank_statement's own local
# closures are left untouched — this only reuses its keyword *knowledge*,
# not its code path, since refactoring that function's three slightly-
# different narration keyword sets risks behavior changes to a working
# vertical this task doesn't own.
# "cr"/"dr" deliberately excluded: find_column() matches on substring, and
# those two-letter tokens collide with ordinary words that have nothing to do
# with credit/debit (e.g. "description" contains "cr", "address" contains
# "dr") -- confirmed empirically against the real scanwick_bank_*.csv fixtures,
# where this previously caused `description` to be misdetected as the credit
# column, silently zeroing every credit-side transaction's amount. The
# dedicated Dr/Cr-indicator-column case is already handled separately and
# more precisely by _TYPE_KEYWORDS ("drcr", "dr_cr").
_CREDIT_KEYWORDS = ["credit", "credits", "inflow", "receipt", "deposit"]
_DEBIT_KEYWORDS = ["debit", "debits", "outflow", "withdrawal", "expense", "payment"]
_TYPE_KEYWORDS = ["type", "drcr", "dr_cr", "indicator", "transaction_type"]
_BALANCE_KEYWORDS = ["balance", "closing_balance", "running_balance"]
_NARRATION_KEYWORDS = ["narration", "description", "payee", "remarks", "particulars", "memo"]
_CURRENCY_KEYWORDS = ["currency", "ccy"]
# Same list /api/analyze's _find_account_number_column (app/routes/analyze.py) uses.
_ACCOUNT_NUMBER_KEYWORDS = ["account_number", "account_no", "acc_no", "acc_number", "iban", "account_id", "bank_account"]


def _clean_str_or_none(value) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def _normalize_payee(description: Optional[str]) -> Optional[str]:
    """Best-effort cleanup, not a full payee-matching engine: collapses
    whitespace and title-cases the raw narration text."""
    cleaned = _clean_str_or_none(description)
    if cleaned is None:
        return None
    return " ".join(cleaned.split()).title()


def _resolve_signed_amount(
    raw: pd.Series, credit_col: Optional[str], debit_col: Optional[str], type_col: Optional[str], amount_col: Optional[str]
) -> Optional[Decimal]:
    """Same 5-case precedence as _analyze_bank_statement's Case A-E, applied
    per row (one signed Decimal) instead of as an aggregate series."""
    if credit_col and debit_col and credit_col != debit_col:
        credit = _kobo_or_none(raw.get(credit_col)) or 0
        debit = _kobo_or_none(raw.get(debit_col)) or 0
        return credit - abs(debit)
    if type_col and amount_col:
        amount = _kobo_or_none(raw.get(amount_col))
        if amount is None:
            return None
        is_credit = str(raw.get(type_col)).strip().lower() in ("credit", "cr", "deposit", "in", "receipt", "positive", "c")
        return abs(amount) if is_credit else -abs(amount)
    if amount_col:
        return _kobo_or_none(raw.get(amount_col))
    if credit_col and not debit_col:
        return _kobo_or_none(raw.get(credit_col))
    if debit_col and not credit_col:
        debit = _kobo_or_none(raw.get(debit_col))
        return -abs(debit) if debit is not None else None
    return None


def score_bank_columns(df: pd.DataFrame) -> float:
    """How closely this dataframe's columns match a bank-statement shape —
    used by dataset_detection.py to auto-identify an uploaded file's type
    before the user has to say so. Reuses the exact same column-detection
    keyword lists extract_canonical_bank_rows() uses for real ingestion, so
    detection and ingestion can never disagree about what "looks like a
    bank statement" means. Four independent signals (date, an amount
    signal, balance, narration), each worth an equal quarter — a real bank
    statement should have all four; a sales or e-commerce export won't."""
    date_col = find_column(df, COLUMN_CANDIDATES["date"])
    credit_col = find_column(df, _CREDIT_KEYWORDS)
    debit_col = find_column(df, _DEBIT_KEYWORDS)
    amount_col = find_column(df, COLUMN_CANDIDATES["amount"])
    balance_col = find_column(df, _BALANCE_KEYWORDS)
    narration_col = find_column(df, _NARRATION_KEYWORDS)

    signals = [
        bool(date_col),
        bool((credit_col and debit_col) or amount_col),
        bool(balance_col),
        bool(narration_col),
    ]
    return sum(signals) / len(signals)


def extract_canonical_bank_rows(
    df: pd.DataFrame, mapping: Optional[dict[str, str]] = None, value_rules: Optional[dict] = None
) -> list[dict]:
    """Maps a generic bank-statement CSV into canonical row dicts — one per
    row. Column detection reuses find_column() (already public/module-level
    in utils/analyzer.py) with the same keyword knowledge the existing
    bank-statement industry analyzer and /api/analyze's account-number
    detection already encode.

    `mapping` (Data Mapping Layer, {user_header: canonical_field}) takes
    priority over the keyword-based find_column() detection when provided —
    the same columns (date/credit/debit/type/amount/balance/narration/
    currency) feed the existing 5-case _resolve_signed_amount logic either
    way, unchanged; only how each is located differs.

    `value_rules` (3.7) carries the mapping's persisted `date_locale`
    ("day_first"/"month_first") -- see `app.utils.locale_dates`. Each row
    dict carries an internal `_row_warning` (None, or an AMBIGUOUS_DATE/
    INVALID_DATE dict) for `compute_bank_quality_report` to turn into a
    named, row-referenced warning; it is never written to
    `BankTransaction`."""
    date_locale = (value_rules or {}).get("date_locale")
    if mapping:
        override_map = {canonical: header for header, canonical in mapping.items()}

        def _col(canonical_field: str) -> Optional[str]:
            header = override_map.get(canonical_field)
            return header if header in df.columns else None

        date_col = _col("transaction_date")
        credit_col = _col("credit_amount")
        debit_col = _col("debit_amount")
        type_col = _col("transaction_type")
        amount_col = _col("amount")
        balance_col = _col("balance_after")
        narration_col = _col("description")
        currency_col = _col("currency")
    else:
        date_col = find_column(df, COLUMN_CANDIDATES["date"])
        credit_col = find_column(df, _CREDIT_KEYWORDS)
        debit_col = find_column(df, _DEBIT_KEYWORDS)
        type_col = find_column(df, _TYPE_KEYWORDS)
        amount_col = find_column(df, COLUMN_CANDIDATES["amount"])
        balance_col = find_column(df, _BALANCE_KEYWORDS)
        narration_col = find_column(df, _NARRATION_KEYWORDS)
        currency_col = find_column(df, _CURRENCY_KEYWORDS)

    rows = []
    for row_position, (_, raw) in enumerate(df.iterrows()):
        date_warning = None
        transaction_date = None
        if date_col:
            transaction_date_raw, date_warning = parse_locale_date(raw.get(date_col), date_locale)
            if transaction_date_raw is not None:
                transaction_date = transaction_date_raw.date()
            if date_warning is not None:
                date_warning = {**date_warning, "row": row_position, "field": "transaction_date"}
        description = _clean_str_or_none(raw.get(narration_col)) if narration_col else None
        signed_amount = _resolve_signed_amount(raw, credit_col, debit_col, type_col, amount_col)

        rows.append(
            {
                "transaction_date": transaction_date,
                "description": description,
                "payee_normalized": _normalize_payee(description),
                "amount": signed_amount,
                "original_currency": (_clean_str_or_none(raw.get(currency_col)) if currency_col else None) or "NGN",
                "_row_warning": date_warning,
                "type": (
                    TransactionType.credit if signed_amount is not None and signed_amount >= 0 else TransactionType.debit
                ),
                "balance_after": _kobo_or_none(raw.get(balance_col)) if balance_col else None,
            }
        )
    return rows


def _is_bank_row_rejected(row: dict) -> bool:
    """transaction_date and amount are NOT NULL on bank_transactions — a row
    missing either (e.g. no credit/debit/amount column could be detected at
    all) can't become a row, same reasoning as the other two ingestion
    paths."""
    return row["transaction_date"] is None or row["amount"] is None


def _resolve_account_number_hash(df: pd.DataFrame, upload_id: str, mapping: Optional[dict[str, str]] = None) -> str:
    """Generic transaction-list exports often don't repeat the account
    number on every row (that's statement-header metadata, not a column) —
    if no such column is found, falls back to a hash of the upload_id
    itself, clearly not a real account number, just enough to satisfy the
    NOT NULL constraint honestly rather than fabricating a fake one."""
    if mapping:
        override_map = {canonical: header for header, canonical in mapping.items()}
        account_col = override_map.get("account_number")
        account_col = account_col if account_col in df.columns else None
    else:
        account_col = find_column(df, _ACCOUNT_NUMBER_KEYWORDS)
    if account_col:
        for value in df[account_col].dropna():
            cleaned = _clean_str_or_none(value)
            if cleaned:
                return hash_value(cleaned)
    return hash_value(f"unknown-account:{upload_id}")


def _compute_date_gaps(sorted_distinct_dates: list) -> list[dict]:
    """Flags any silence longer than GAP_THRESHOLD_DAYS between two
    consecutive days that have at least one transaction."""
    gaps = []
    for previous, current in zip(sorted_distinct_dates, sorted_distinct_dates[1:]):
        gap_days = (current - previous).days
        if gap_days > GAP_THRESHOLD_DAYS:
            gaps.append(
                {
                    "gap_start": (previous + timedelta(days=1)).isoformat(),
                    "gap_end": (current - timedelta(days=1)).isoformat(),
                    "days": gap_days - 1,
                }
            )
    return gaps


def _serialize_integrity(integrity: dict) -> dict:
    """Decimal fields aren't JSON-serializable as-is (needed when persisting
    into uploads.analyzer_metadata, a JSON column) — converts them to float,
    leaving None/bool fields untouched."""
    return {key: (float(value) if isinstance(value, Decimal) else value) for key, value in integrity.items()}


def compute_bank_quality_report(canonical_rows: list[dict], integrity: dict) -> dict:
    """Data-quality report for the Bank vertical per task 1.26:
    transactions_parsed, date_range, months_of_data, balance_integrity,
    date_gaps, warnings. Operates on already-extracted canonical rows/
    integrity so it describes exactly what write_canonical_bank_rows/
    ingest_bank_dataframe will actually persist — same reasoning as
    compute_ecommerce_quality_report (task 1.11)."""
    parsed_rows = [r for r in canonical_rows if not _is_bank_row_rejected(r)]
    rows_rejected = len(canonical_rows) - len(parsed_rows)

    # 3.7: "every rejected row must produce a named warning with row
    # reference, canonical field, reason/code, raw value only when safe,
    # and remediation" -- `_row_warning` (set by extract_canonical_bank_rows
    # for an AMBIGUOUS_DATE/INVALID_DATE cell) already has that shape; a row
    # rejected for a plain missing transaction_date/amount (no detection
    # column at all, or a genuinely blank cell) gets an equivalent synthesized
    # one so no rejected row is ever unaccounted for.
    rejected_rows = []
    for row_position, row in enumerate(canonical_rows):
        if not _is_bank_row_rejected(row):
            continue
        warning = row.get("_row_warning")
        if warning is not None:
            rejected_rows.append(warning)
            continue
        missing_fields = [
            field for field, present in (("transaction_date", row["transaction_date"]), ("amount", row["amount"])) if present is None
        ]
        rejected_rows.append(
            {
                "row": row_position,
                "field": "/".join(missing_fields),
                "code": "MISSING_REQUIRED_FIELD",
                "message": f"Row {row_position} could not be resolved: missing {', '.join(missing_fields)}.",
                "raw_value": None,
                "remediation": "Confirm the column mapping for this field and re-upload.",
            }
        )

    txn_dates = sorted(r["transaction_date"] for r in parsed_rows)
    date_range_start = txn_dates[0] if txn_dates else None
    date_range_end = txn_dates[-1] if txn_dates else None

    # Same "distinct calendar months present" definition monthly_cashflow()
    # (bank_cashflow.py) and MIN_MONTHS_FOR_INCOME_STABILITY already use
    # elsewhere in this vertical — not a separate days_of_history/30 estimate.
    months_of_data = len({d.strftime("%Y-%m") for d in txn_dates})

    date_gaps = _compute_date_gaps(sorted(set(txn_dates)))

    warnings = []
    if rows_rejected > 0:
        warnings.append(
            {
                "field": "transaction_date/amount",
                "severity": "medium",
                "message": (
                    f"{rows_rejected} of {len(canonical_rows)} rows were rejected "
                    "(transaction_date or amount could not be resolved)."
                ),
                "features_disabled": [],
            }
        )
    if integrity.get("balance_integrity_passed") is False:
        warnings.append(
            {
                "field": "balance_integrity",
                "severity": "high",
                "message": (
                    "Opening balance + credits - debits does not reconcile with the stated "
                    f"closing balance (discrepancy: {integrity['balance_discrepancy']})."
                ),
                "features_disabled": [],
            }
        )

    return {
        "transactions_parsed": len(parsed_rows),
        "rows_rejected": rows_rejected,
        "rejected_rows": rejected_rows,
        "date_range_start": date_range_start,
        "date_range_end": date_range_end,
        "months_of_data": months_of_data,
        "balance_integrity": integrity,
        "date_gaps": date_gaps,
        "warnings": warnings,
    }


async def write_canonical_bank_rows(
    db: AsyncSession,
    canonical_rows: list[dict],
    account_id: uuid.UUID,
    source: BankTransactionDataSource,
    *,
    merchant_id: uuid.UUID,
    base_currency: str = "NGN",
) -> dict:
    """merchant_id scopes contextual-marker lookup the same way
    Order.merchant_id does for the other vertical (task
    1.25) — bank_transactions has no merchant/user column of its own (that
    lives on the parent `accounts` row via Account.user_id), so callers pass
    the account owner's user_id through as merchant_id. base_currency is the
    account's own currency (real, from Mono; "NGN" default for CSV/OCR,
    task 1.21/1.22) — conversion is a same-currency 1.0 rate whenever
    original_currency already equals it."""
    transactions_created = 0
    rows_rejected = 0
    duplicates_skipped = 0
    marker_ranges = await get_marker_ranges(db, merchant_id, AnalyzerType.bank)
    # Audit #14: re-uploading the same statement (or a client retry) used to
    # blindly insert every row again, silently doubling cashflow/revenue
    # figures. One query fetches this account's existing (date, amount,
    # description) triples up front — a conservative natural key for "this
    # exact transaction already exists" — so the per-row check below is an
    # in-memory set lookup, not a second N+1 query pattern.
    existing_keys = {
        (t.transaction_date, t.amount, t.description)
        for t in (
            await db.execute(
                select(
                    BankTransaction.transaction_date, BankTransaction.amount, BankTransaction.description
                ).where(BankTransaction.account_id == account_id)
            )
        ).all()
    }
    # Audit #19: get_historical_rate was previously awaited once per row
    # inside this loop — on a large multi-currency statement, that's one DB
    # round trip per row, serially. Memoized per unique (currency, date)
    # pair actually seen in this batch, so a repeated pair (the overwhelming
    # common case — most rows share a currency, many share a date) costs
    # nothing beyond the first lookup.
    rate_cache: dict[tuple[str, date], Optional[Decimal]] = {}
    for row in canonical_rows:
        if _is_bank_row_rejected(row):
            rows_rejected += 1
            continue

        dedup_key = (row["transaction_date"], row["amount"], row["description"])
        if dedup_key in existing_keys:
            duplicates_skipped += 1
            continue
        existing_keys.add(dedup_key)

        rate_key = (row["original_currency"], row["transaction_date"])
        if rate_key not in rate_cache:
            rate_cache[rate_key] = await get_historical_rate(
                db, row["original_currency"], base_currency, row["transaction_date"]
            )
        exchange_rate = rate_cache[rate_key]
        base_currency_amount = (row["amount"] * exchange_rate) if exchange_rate is not None else None

        txn = BankTransaction(
            id=uuid.uuid4(),
            account_id=account_id,
            transaction_date=row["transaction_date"],
            description=row["description"],
            payee_normalized=row["payee_normalized"],
            amount=row["amount"],
            original_currency=row["original_currency"],
            base_currency_amount=base_currency_amount,
            exchange_rate=exchange_rate,
            type=row["type"],
            balance_after=row["balance_after"],
            data_source=source,
            is_anomalous=is_within_marker_ranges(row["transaction_date"], marker_ranges),
        )
        db.add(txn)
        transactions_created += 1

    await db.commit()
    return {
        "transactions_created": transactions_created,
        "rows_rejected": rows_rejected,
        "duplicates_skipped": duplicates_skipped,
    }


async def ingest_bank_dataframe(
    db: AsyncSession,
    df: pd.DataFrame,
    user_id: uuid.UUID,
    bank_name: Optional[str],
    source: BankTransactionDataSource,
    upload_id: str,
    *,
    account_number_hash_override: Optional[str] = None,
    base_currency: str = "NGN",
    mapping: Optional[dict[str, str]] = None,
    value_rules: Optional[dict] = None,
) -> dict:
    """Core ingestion: creates the parent Account row (including the balance
    integrity fields — task 1.24, run "after parsing" per spec, right here)
    plus all its BankTransaction rows.

    account_number_hash_override/base_currency exist for callers (Mono,
    1.23) that already know the real account number/currency directly from
    a structured API response, rather than having to heuristically detect
    them from tabular data the way CSV/OCR have to. Defaulting both to None/
    "NGN" keeps the CSV (1.21) and PDF/OCR (1.22) call sites' behavior
    unchanged. `mapping`/`value_rules` (Data Mapping Layer) only ever come
    from the CSV path -- PDF/Mono callers never pass them, same None default.
    """
    canonical_rows = extract_canonical_bank_rows(df, mapping, value_rules)
    written_rows = [r for r in canonical_rows if not _is_bank_row_rejected(r)]
    parsed_dates = [r["transaction_date"] for r in written_rows]
    integrity = compute_balance_integrity_for_rows(written_rows)
    quality = compute_bank_quality_report(canonical_rows, integrity)

    account_number_hash = account_number_hash_override or _resolve_account_number_hash(df, upload_id, mapping)

    # Audit #14: every re-upload used to create a brand-new Account with a
    # fresh UUID, even when one already existed for this exact account —
    # splitting one real bank account's history across multiple Account
    # rows and (via write_canonical_bank_rows' per-account transaction
    # scoping) letting every re-upload double-count into a "different"
    # account's totals. Reuses the existing Account when this user has
    # already ingested this same account_number_hash before.
    account = (
        await db.execute(
            select(Account).where(Account.user_id == user_id, Account.account_number_hash == account_number_hash)
        )
    ).scalar_one_or_none()

    if account is None:
        account = Account(id=uuid.uuid4(), user_id=user_id, account_number_hash=account_number_hash)
        db.add(account)

    account.bank_name = bank_name or account.bank_name
    account.base_currency = base_currency
    existing_start = account.statement_period_start
    existing_end = account.statement_period_end
    new_start = min(parsed_dates) if parsed_dates else None
    new_end = max(parsed_dates) if parsed_dates else None
    account.statement_period_start = min(d for d in (existing_start, new_start) if d is not None) if (existing_start or new_start) else None
    account.statement_period_end = max(d for d in (existing_end, new_end) if d is not None) if (existing_end or new_end) else None
    account.opening_balance = integrity["opening_balance"]
    account.closing_balance = integrity["closing_balance"]
    account.computed_closing_balance = integrity["computed_closing_balance"]
    account.balance_integrity_passed = integrity["balance_integrity_passed"]
    account.balance_discrepancy = integrity["balance_discrepancy"]
    await db.commit()

    write_result = await write_canonical_bank_rows(
        db, canonical_rows, account.id, source, merchant_id=user_id, base_currency=base_currency
    )

    # upload_id is a real UUID for the CSV (1.21) and PDF/OCR (1.22) paths,
    # but Mono (1.23) passes its own mono_account_id here instead (no file
    # upload exists to stage) — skip writing an Upload row in that case,
    # consistent with there being no real "upload" to report a quality
    # summary for.
    try:
        upload_uuid = uuid.UUID(upload_id)
    except (ValueError, AttributeError, TypeError):
        upload_uuid = None

    if upload_uuid is not None:
        upload = (await db.execute(select(Upload).where(Upload.id == upload_uuid))).scalar_one_or_none()
        if upload is None:
            upload = Upload(id=upload_uuid, merchant_id=user_id, analyzer_type=AnalyzerType.bank)
            db.add(upload)
        days_of_history = (
            (quality["date_range_end"] - quality["date_range_start"]).days + 1
            if quality["date_range_start"] and quality["date_range_end"]
            else 0
        )
        upload.data_source = source.value
        upload.status = UploadStatus.ready
        upload.rows_parsed = quality["transactions_parsed"]
        upload.rows_rejected = write_result["rows_rejected"]
        upload.date_range_start = quality["date_range_start"]
        upload.date_range_end = quality["date_range_end"]
        upload.days_of_history = days_of_history
        upload.warnings = quality["warnings"]
        upload.analyzer_metadata = {
            "months_of_data": quality["months_of_data"],
            "balance_integrity": _serialize_integrity(quality["balance_integrity"]),
            "date_gaps": quality["date_gaps"],
            "rejected_rows": quality["rejected_rows"],
            **({"mapping_applied": summarize_mapping_applied(mapping, None, value_rules)} if mapping else {}),
        }
        await db.commit()

    return {"account_id": str(account.id), "quality_report": quality, **write_result}


@celery_app.task(name="ingest_bank_csv")
def ingest_bank_csv(
    upload_id: str,
    user_id: str,
    bank_name: Optional[str] = None,
    mapping: Optional[dict[str, str]] = None,
    value_rules: Optional[dict] = None,
) -> dict:
    return asyncio.run(_ingest_bank_csv_async(upload_id, user_id, bank_name, mapping, value_rules))


async def _ingest_bank_csv_async(
    upload_id: str,
    user_id: str,
    bank_name: Optional[str],
    mapping: Optional[dict[str, str]] = None,
    value_rules: Optional[dict] = None,
) -> dict:
    try:
        df = read_staged_upload(upload_id)
        async with async_session() as db:
            result = await ingest_bank_dataframe(
                db,
                df,
                uuid.UUID(user_id),
                bank_name,
                BankTransactionDataSource.generic_csv,
                upload_id,
                mapping=mapping,
                value_rules=value_rules,
            )
    except Exception as exc:
        async with async_session() as db:
            await mark_upload_failed(db, upload_id, uuid.UUID(user_id), AnalyzerType.bank, exc)
        raise
    finally:
        delete_staged_upload(upload_id)
    return result
