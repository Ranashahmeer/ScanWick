import io
import uuid
from typing import Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reconciliation_reports import AnalyzerType
from app.models.uploads import Upload, UploadStatus
from app.services import storage

_STAGING_PREFIX = "staging"


def _staging_key(upload_id: str, extension: str) -> str:
    return f"{_STAGING_PREFIX}/{upload_id}.{extension}"


def stage_upload(upload_id: str, data: bytes, extension: str = "csv") -> None:
    """Writes a just-uploaded file through the shared storage abstraction
    (app/services/storage.py — local disk in dev, S3/R2 in production)
    instead of a fixed local container path. A prior fix (audit #12) gave
    the API and Celery worker a shared Docker volume at /tmp/scanwick_uploads
    so the worker could see what the API staged — but that only works when
    both processes share one host's filesystem. On a platform where the API
    and worker are independently-deployed services (e.g. Railway, with no
    equivalent of a cross-service shared volume), a local write is invisible
    to the worker that later tries to read it back. Routing through the
    existing S3-compatible backend fixes this for any multi-host deployment,
    local dev included (S3FileStorage/LocalFileStorage are already the same
    interface either way)."""
    storage.upload_file(_staging_key(upload_id, extension), data)


_CSV_ENCODING_FALLBACKS = ("utf-8", "cp1252", "latin-1")


def read_csv_bytes(data: bytes) -> pd.DataFrame:
    """Audit #18: a CSV isn't guaranteed to be UTF-8 (a common real-world
    case: Excel's "CSV" export on Windows is actually Windows-1252/cp1252).
    Tries utf-8 first, then falls back through cp1252/latin-1 rather than
    letting a non-UTF-8 export raise an unhandled UnicodeDecodeError deep
    inside a Celery task. Also used directly by dataset_detection.py, which
    classifies an uploaded file's type before anything gets staged."""
    last_error: Optional[UnicodeDecodeError] = None
    for encoding in _CSV_ENCODING_FALLBACKS:
        try:
            return pd.read_csv(io.BytesIO(data), encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    raise last_error


def read_staged_bytes(upload_id: str, extension: str) -> bytes:
    """Raw-bytes reader for a staged file that isn't a CSV/XLSX dataframe —
    e.g. a PDF statement, read directly by bank_pdf_ingestion.py's own text
    extraction rather than through pandas."""
    return storage.download_file(_staging_key(upload_id, extension))


def read_staged_csv(upload_id: str) -> pd.DataFrame:
    """CSV-only reader — for callers that only ever stage a `.csv` file and
    expect exactly that back."""
    return read_csv_bytes(storage.download_file(_staging_key(upload_id, "csv")))


def read_staged_upload(upload_id: str) -> pd.DataFrame:
    """XLSX-aware: tries `{upload_id}.xlsx` first, falling back to
    `{upload_id}.csv` when no XLSX was staged. Every ingestion task's
    upload_id resolves to the same file either way — the only caller today
    (POST /api/v1/upload/csv) always stages `.csv`, so this fallback is
    forward-looking for a future XLSX upload path, same as before this was
    storage-backed. Requires the `openpyxl` engine for `.xlsx` (declared in
    pyproject.toml/requirements.txt)."""
    try:
        data = storage.download_file(_staging_key(upload_id, "xlsx"))
        return pd.read_excel(io.BytesIO(data))
    except Exception:
        return read_staged_csv(upload_id)


def delete_staged_upload(upload_id: str) -> None:
    """Audit #16: staged files were never cleaned up — every CSV/PDF staged
    for ingestion was left on disk forever regardless of success or
    failure, an unbounded resource leak. Called from a `finally` block once
    the ingestion task has read the file's contents into memory/DB, whether
    that succeeded or raised. Deletes every possible extension
    unconditionally (harmless no-op for whichever ones weren't actually
    staged — both storage backends' delete_file is already idempotent)
    rather than tracking which one was used."""
    for extension in ("csv", "xlsx", "pdf"):
        storage.delete_file(_staging_key(upload_id, extension))


async def mark_upload_failed(
    db: AsyncSession, upload_id: str, merchant_id: uuid.UUID, analyzer_type: AnalyzerType, error: Exception
) -> None:
    """Audit #13: no code anywhere ever set Upload.status to `failed` — any
    exception during ingestion left the row stuck at `processing` forever,
    so GET /quality-report polled a status that would never change. Called
    from every ingestion task's except-block. `merchant_id`/`analyzer_type`
    are needed to create the Upload row from scratch if ingestion failed
    before one existed yet (e.g. the staged file itself couldn't be read) —
    both columns are NOT NULL, so they can't be left unset."""
    try:
        upload_uuid = uuid.UUID(upload_id)
    except (ValueError, AttributeError, TypeError):
        return  # Mono's synthetic "upload_id" (mono_account_id) — no real Upload row to update.

    upload = (await db.execute(select(Upload).where(Upload.id == upload_uuid))).scalar_one_or_none()
    if upload is None:
        upload = Upload(id=upload_uuid, merchant_id=merchant_id, analyzer_type=analyzer_type)
        db.add(upload)
    upload.status = UploadStatus.failed
    upload.error_message = str(error)[:2000]
    await db.commit()
