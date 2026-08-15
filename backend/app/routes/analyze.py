import io
import logging
from pathlib import PurePosixPath
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.database import get_db
from app.dependencies import get_current_user
from app.models import BankAccountIdentifier, User
from app.services.encryption import encrypt_field, hash_value
from app.services.entitlements import gate_premium_components
from app.services.storage import upload_file
from app.utils.analyzer import analyze_data

router = APIRouter(prefix="/api/analyze", tags=["analyze"])
logger = logging.getLogger(__name__)

_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "text/plain",
    "application/octet-stream",
}
_ACCOUNT_NUMBER_KEYWORDS = (
    "account_number",
    "account_no",
    "acc_no",
    "acc_number",
    "iban",
    "account_id",
    "bank_account",
)


def _find_account_number_column(df: pd.DataFrame) -> str | None:
    for col in df.columns:
        col_normalized = col.lower().replace(" ", "_")
        if any(kw in col_normalized for kw in _ACCOUNT_NUMBER_KEYWORDS):
            return col
    return None


async def _persist_account_identifiers(db: AsyncSession, user_id: int, df: pd.DataFrame) -> None:
    """Record which bank accounts this user has uploaded statements for.

    Never stores the raw account number — only its one-way hash (for
    matching/dedup) and a Fernet-encrypted copy (for the rare case the
    actual number needs to be read back).
    """
    account_col = _find_account_number_column(df)
    if not account_col:
        return

    raw_numbers = {
        str(v).strip() for v in df[account_col].dropna().unique() if str(v).strip()
    }
    for raw_number in raw_numbers:
        account_hash = hash_value(raw_number)
        existing = await db.execute(
            select(BankAccountIdentifier).where(
                BankAccountIdentifier.user_id == user_id,
                BankAccountIdentifier.account_number_hash == account_hash,
            )
        )
        if existing.scalars().first() is not None:
            continue
        db.add(
            BankAccountIdentifier(
                user_id=user_id,
                account_number_hash=account_hash,
                account_number_encrypted=encrypt_field(raw_number),
            )
        )
    await db.commit()


@router.post("", summary="Analyze a CSV file")
async def analyze_csv(
    file: UploadFile = File(..., description="CSV file to analyze"),
    date_from: str | None = Query(None, description="Filter rows from this date (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="Filter rows up to this date (YYYY-MM-DD)"),
    industry: str | None = Query(None, description="Override auto-detected industry"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in _ALLOWED_CONTENT_TYPES and not (
        file.filename and file.filename.lower().endswith(".csv")
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only CSV files are supported.",
        )

    raw = await file.read()
    if len(raw) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 10 MB limit.",
        )

    safe_filename = PurePosixPath(file.filename or "upload.csv").name
    storage_key = f"analyze/{uuid4().hex}_{safe_filename}"
    try:
        await run_in_threadpool(upload_file, storage_key, raw)
    except Exception:
        logger.exception("Failed to persist uploaded CSV %r to storage", storage_key)

    try:
        df = pd.read_csv(io.BytesIO(raw), low_memory=False)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse CSV: {exc}",
        )

    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The uploaded CSV contains no data rows.",
        )

    result = analyze_data(
        df,
        date_from=date_from,
        date_to=date_to,
        industry_override=industry,
    )

    if result.get("dataset_type") == "bank_statement":
        try:
            await _persist_account_identifiers(db, user_id=user.id, df=df)
        except Exception:
            logger.exception("Failed to persist bank account identifiers")

    if "health_score" in result and "components" in result["health_score"]:
        result["health_score"]["components"] = gate_premium_components(
            result["health_score"]["components"], user.subscription_tier
        )

    return result
