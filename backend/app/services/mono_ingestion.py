import asyncio
import uuid
from decimal import Decimal
from typing import Optional

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery_app
from app.database import async_session
from app.models.bank_transactions import BankTransactionDataSource
from app.services.bank_ingestion import ingest_bank_dataframe
from app.services.encryption import hash_value
from app.services.mono_client import fetch_account_details, fetch_all_account_transactions

# Mono reports amounts/balances in the currency's minor unit (kobo for NGN,
# pesewas for GHS, cents for KES) across NG/GH/KE alike — divide by 100 to
# get the major-unit Decimal value used everywhere else in this schema.
_MINOR_UNIT_DIVISOR = 100


def _minor_to_major(value) -> Optional[int]:
    if value is None:
        return None
    return int(str(value))


def mono_transactions_to_dataframe(transactions: list[dict]) -> pd.DataFrame:
    """Maps Mono's transaction JSON into the same date/narration/debit/
    credit/balance column shape the CSV fixture (1.21) uses, so it feeds the
    exact same extract_canonical_bank_rows()/ingest_bank_dataframe() the CSV
    and PDF/OCR (1.22) paths use — unmodified. Unlike CSV/OCR, Mono already
    tells us the direction explicitly via a `type` field, so there's no
    credit/debit-column-detection heuristic needed: this always populates
    exactly one of debit/credit per row directly from that field."""
    rows = []
    for txn in transactions:
        amount = _minor_to_major(txn.get("amount"))
        is_credit = str(txn.get("type", "")).lower() == "credit"
        rows.append(
            {
                "date": txn.get("date"),
                "narration": txn.get("narration"),
                "debit": None if is_credit else amount,
                "credit": amount if is_credit else None,
                "balance": _minor_to_major(txn.get("balance")),
            }
        )
    return pd.DataFrame(rows, columns=["date", "narration", "debit", "credit", "balance"])


async def ingest_mono_account(db: AsyncSession, user_id: uuid.UUID, mono_account_id: str) -> dict:
    """Connects to Mono directly — no file upload at all — and feeds the
    result through the same canonical bank-ingestion pipeline as the CSV
    (1.21) and PDF/OCR (1.22) paths, via ingest_bank_dataframe(). Unlike
    those two, Mono gives us the account's real number/currency/bank name
    directly via fetch_account_details(), so those are passed through
    rather than heuristically detected."""
    account_details = await fetch_account_details(mono_account_id)
    transactions = await fetch_all_account_transactions(mono_account_id)

    institution = account_details.get("institution") or {}
    bank_name = institution.get("name")
    base_currency = account_details.get("currency") or "NGN"
    real_account_number = account_details.get("accountNumber")
    account_number_hash = (
        hash_value(real_account_number)
        if real_account_number
        else hash_value(f"unknown-mono-account:{mono_account_id}")
    )

    df = mono_transactions_to_dataframe(transactions)
    return await ingest_bank_dataframe(
        db,
        df,
        user_id,
        bank_name,
        BankTransactionDataSource.mono_api,
        upload_id=mono_account_id,  # no file upload to stage for Mono; unused since the hash override below is always set
        account_number_hash_override=account_number_hash,
        base_currency=base_currency,
    )


@celery_app.task(name="ingest_mono_account")
def ingest_mono_account_task(user_id: str, mono_account_id: str) -> dict:
    return asyncio.run(_ingest_mono_account_async(user_id, mono_account_id))


async def _ingest_mono_account_async(user_id: str, mono_account_id: str) -> dict:
    async with async_session() as db:
        return await ingest_mono_account(db, uuid.UUID(user_id), mono_account_id)
