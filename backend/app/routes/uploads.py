import logging
from uuid import UUID, uuid4

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.database import get_db
from app.dependencies import get_current_user
from app.models import (
    AnalyzerType,
    BankRole,
    EcommerceRole,
    OrderDataSource,
    Upload,
    UploadStatus,
    User,
    Vertical,
)
from app.schemas.envelope import error_response, success_response
from app.services.bank_ingestion import ingest_bank_csv
from app.services.column_mapping import compute_source_signature, resolve_mapping
from app.services.column_mapping_store import get_saved_mapping, upsert_mapping
from app.services.dataset_detection import detect_dataset_type_async
from app.services.ecommerce_ingestion import ingest_ecommerce_csv
from app.services.rbac import check_any_role, check_role
from app.services.upload_staging import (
    delete_staged_upload,
    mark_upload_failed,
    read_csv_bytes,
    read_staged_upload,
    stage_upload,
)

# Shared across both analyzers per spec (GET /api/v1/upload/{upload_id}/quality-report
# is not under /api/v1/ecommerce) — built here first for the e-commerce path (step 1.11);
# bank writes its own quality fields into the same `uploads` table via its
# own Celery ingestion task (see POST /api/v1/upload/csv below).
router = APIRouter(prefix="/api/v1/upload", tags=["upload"])
logger = logging.getLogger(__name__)

_MAX_BYTES = 10 * 1024 * 1024  # 10 MB, same limit as /api/analyze

# Who's allowed to kick off an ingestion run per vertical. Deliberately
# tighter than each vertical's READ_ROLES (dashboard.py-style routes) —
# uploading a full data export is a batch write, not a read, so viewer
# roles are excluded even though they can view the resulting dashboards.
_INGEST_ROLES = {
    Vertical.ecommerce: {EcommerceRole.owner.value, EcommerceRole.admin.value, EcommerceRole.manager.value},
    Vertical.bank: {BankRole.bank_owner.value, BankRole.bank_admin.value},
}


def _serialize(upload: Upload) -> dict:
    return {
        "upload_id": str(upload.id),
        "status": upload.status.value,
        "rows_parsed": upload.rows_parsed,
        "rows_rejected": upload.rows_rejected,
        "date_range": {
            "start": upload.date_range_start.isoformat() if upload.date_range_start else None,
            "end": upload.date_range_end.isoformat() if upload.date_range_end else None,
        },
        "days_of_history": upload.days_of_history,
        "warnings": upload.warnings or [],
        # Only these sub-keys are exposed, not the whole analyzer_metadata
        # blob — that JSON column also holds unrelated per-vertical
        # internals (e.g. bank's months_of_data/balance_integrity/
        # date_gaps) that shouldn't leak into the generic response.
        "mapping_applied": (upload.analyzer_metadata or {}).get("mapping_applied"),
        # 3.7: named, row-referenced rejection detail (row/field/code/
        # raw_value/remediation) -- see ecommerce_ingestion.py's
        # compute_ecommerce_quality_report.
        "rejected_rows": (upload.analyzer_metadata or {}).get("rejected_rows", []),
    }


@router.get("/{upload_id}/quality-report")
async def get_quality_report(
    upload_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        uid = UUID(upload_id)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content=error_response("INVALID_UPLOAD_ID", f"'{upload_id}' is not a valid UUID."),
        )

    result = await db.execute(select(Upload).where(Upload.id == uid))
    upload = result.scalar_one_or_none()

    if upload is None:
        return JSONResponse(
            status_code=404,
            content=error_response("UPLOAD_NOT_FOUND", f"No upload found for upload_id {upload_id}."),
        )

    # This route previously had no auth at all — any caller who guessed a
    # UUID could read another merchant's data-quality report. Any granted
    # role for this merchant/vertical is enough (matches reconciliation.py's
    # get_reconciliation_report — this is a read, not a write).
    # Upload.analyzer_type (AnalyzerType) and Vertical are separate enum
    # classes with matching values, not interchangeable — convert explicitly.
    error, _ = await check_any_role(db, current_user, upload.merchant_id, Vertical(upload.analyzer_type.value))
    if error is not None:
        return error

    return success_response(_serialize(upload))


@router.post("/detect")
async def detect_upload_type(
    file: UploadFile = File(..., description="CSV file to classify (bank statement / CRM export / order export)"),
    current_user: User = Depends(get_current_user),
):
    """Classifies a CSV's likely vertical from its column headers alone,
    before the user has to say whether it's a bank statement, CRM export,
    or store-orders export. Stateless — reads the file into memory only,
    writes nothing, no merchant scoping needed (nothing merchant-specific
    is touched). The actual POST /csv call still needs an explicit
    analyzer_type; this just lets the frontend fill that in automatically
    instead of asking the user to guess correctly up front."""
    if not (file.filename and file.filename.lower().endswith(".csv")):
        return JSONResponse(
            status_code=415,
            content=error_response("UNSUPPORTED_FILE_TYPE", "Only CSV files are supported."),
        )

    raw = await file.read()
    if len(raw) > _MAX_BYTES:
        return JSONResponse(
            status_code=413,
            content=error_response("FILE_TOO_LARGE", "File exceeds the 10 MB limit."),
        )
    if not raw:
        return JSONResponse(
            status_code=422,
            content=error_response("EMPTY_FILE", "The uploaded file is empty."),
        )

    def _read() -> pd.DataFrame:
        return read_csv_bytes(raw)

    try:
        df = await run_in_threadpool(_read)
    except UnicodeDecodeError:
        return JSONResponse(
            status_code=422,
            content=error_response("UNREADABLE_FILE", "Could not read this file as CSV text."),
        )
    except Exception:
        logger.exception("Failed to parse CSV for type detection")
        return JSONResponse(
            status_code=422,
            content=error_response("UNPARSEABLE_FILE", "Could not parse this file as CSV."),
        )

    result = await detect_dataset_type_async(df)
    return success_response(
        {
            "analyzer_type": result.analyzer_type,
            "source": result.source,
            "confidence": round(result.confidence, 2),
            "scores": {key: round(value, 2) for key, value in result.scores.items()},
            "via_llm": result.via_llm,
        }
    )


def _ingest_vertical_task(vertical: Vertical):
    return {Vertical.ecommerce: ingest_ecommerce_csv, Vertical.bank: ingest_bank_csv}[vertical]


async def _dispatch_ingestion(
    db: AsyncSession,
    upload: Upload,
    vertical: Vertical,
    mapping: dict | None,
    source: str | None,
    bank_name: str | None,
    value_rules: dict | None = None,
) -> JSONResponse | None:
    """Shared by the auto-apply fast path in POST /csv and POST
    /mapping/confirm — sets the row to `processing` and dispatches the
    ingestion task with the resolved column mapping frozen in as a task
    argument (see column_mapping.py's module docstring for why: it freezes
    exactly what was approved for *this* upload, immune to a later edit of
    the saved ColumnMapping row). Returns an error JSONResponse on dispatch
    failure (audit #15's existing failure handling, unchanged), None on
    success.

    Dispatched via run_in_threadpool for the same reason the original code
    was: in local dev with CELERY_TASK_ALWAYS_EAGER on, `.delay()` runs the
    task inline, and that task calls asyncio.run() internally -- unsafe from
    directly inside this already-running event loop, safe from a threadpool
    thread."""
    upload.status = UploadStatus.processing
    await db.commit()

    task = _ingest_vertical_task(vertical)
    try:
        if vertical == Vertical.bank:
            await run_in_threadpool(
                task.delay, str(upload.id), str(upload.merchant_id), bank_name, mapping, value_rules
            )
        else:
            await run_in_threadpool(
                task.delay, str(upload.id), str(upload.merchant_id), source, mapping, value_rules
            )
    except Exception as exc:
        logger.exception("Failed to dispatch ingestion task for upload_id %s", upload.id)
        await mark_upload_failed(db, str(upload.id), upload.merchant_id, AnalyzerType(vertical.value), exc)
        delete_staged_upload(str(upload.id))
        return JSONResponse(
            status_code=502,
            content=error_response("DISPATCH_FAILED", "Could not start processing the file. Please try again."),
        )
    return None


@router.post("/csv", status_code=status.HTTP_202_ACCEPTED)
async def upload_csv(
    file: UploadFile = File(..., description="CSV export to ingest"),
    analyzer_type: str = Form(..., description="ecommerce | bank"),
    merchant_id: str = Form(...),
    source: str | None = Form(None, description="Required for ecommerce — the export's platform"),
    bank_name: str | None = Form(None, description="Bank-only, e.g. 'GTBank'"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        vertical = Vertical(analyzer_type)
    except ValueError:
        return JSONResponse(
            status_code=422,
            content=error_response(
                "INVALID_ANALYZER_TYPE", f"'{analyzer_type}' must be one of: ecommerce, bank."
            ),
        )

    try:
        merchant_uuid = UUID(merchant_id)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content=error_response("INVALID_MERCHANT_ID", f"'{merchant_id}' is not a valid UUID."),
        )

    error, _ = await check_role(db, current_user, merchant_uuid, vertical, _INGEST_ROLES[vertical])
    if error is not None:
        return error

    if vertical == Vertical.ecommerce:
        try:
            OrderDataSource(source)
        except ValueError:
            return JSONResponse(
                status_code=422,
                content=error_response(
                    "INVALID_SOURCE",
                    f"'{source}' must be one of: {', '.join(s.value for s in OrderDataSource)}.",
                ),
            )
    # Bank CSV ingestion always uses BankTransactionDataSource.generic_csv
    # internally (see ingest_bank_csv) — no caller-supplied source for it.

    # Audit #17: content_type alone used to be enough to pass this check —
    # since _ALLOWED_CONTENT_TYPES includes the generic, client-controlled,
    # trivially-spoofable "application/octet-stream", a non-CSV file
    # mislabeled with that content-type sailed through regardless of its
    # actual filename/extension. The filename extension is now the sole,
    # unconditional gate; content_type is no longer sufficient on its own.
    if not (file.filename and file.filename.lower().endswith(".csv")):
        return JSONResponse(
            status_code=415,
            content=error_response("UNSUPPORTED_FILE_TYPE", "Only CSV files are supported."),
        )

    raw = await file.read()
    if len(raw) > _MAX_BYTES:
        return JSONResponse(
            status_code=413,
            content=error_response("FILE_TOO_LARGE", "File exceeds the 10 MB limit."),
        )
    if not raw:
        return JSONResponse(
            status_code=422,
            content=error_response("EMPTY_FILE", "The uploaded file is empty."),
        )

    upload_id = uuid4()

    try:
        await run_in_threadpool(stage_upload, str(upload_id), raw, "csv")
    except Exception:
        logger.exception("Failed to stage uploaded CSV for upload_id %s", upload_id)
        return JSONResponse(
            status_code=500,
            content=error_response("STAGING_FAILED", "Could not accept the file. Please try again."),
        )

    # Data Mapping Layer: resolve column headers -> canonical fields before
    # ingesting. `data_source` doubles as the staging slot for `source`
    # (ecommerce) or `bank_name` (bank) between now and whenever
    # ingestion actually dispatches — bank has no real data_source variance
    # today (ingest_bank_csv always uses BankTransactionDataSource.generic_csv
    # internally), so the column isn't otherwise in use for bank uploads.
    display_source = bank_name if vertical == Vertical.bank else source
    analyzer_type = AnalyzerType(vertical.value)

    try:
        df = await run_in_threadpool(read_staged_upload, str(upload_id))
    except Exception:
        logger.exception("Failed to read staged CSV for upload_id %s", upload_id)
        delete_staged_upload(str(upload_id))
        return JSONResponse(
            status_code=422,
            content=error_response("UNPARSEABLE_FILE", "Could not parse this file as CSV."),
        )

    columns = list(df.columns)
    signature = compute_source_signature(columns, analyzer_type)

    saved = await get_saved_mapping(db, merchant_uuid, analyzer_type, signature)
    if saved is not None:
        resolved_mapping: dict = saved.mapping
        value_rules: dict = saved.value_rules or {}
        needs_review = False
    else:
        result = resolve_mapping(columns, analyzer_type)
        resolved_mapping = result.confirmed_mapping()
        value_rules = {}
        # Only genuine ambiguity (needs_confirmation) blocks auto-apply — an
        # unmapped header is just a column nothing could confidently be
        # guessed for (an internal ID, a notes column, a required field
        # that's simply absent from this file entirely); it surfaces as a
        # named warning / disabled-feature downstream (existing convention),
        # not a forced manual review of every upload that has an extra
        # column nobody cares about.
        needs_review = bool(result.needs_confirmation)
        if not needs_review:
            await upsert_mapping(
                db,
                merchant_id=merchant_uuid,
                analyzer_type=analyzer_type,
                source_signature=signature,
                mapping=resolved_mapping,
                unmapped_headers=[u.user_header for u in result.unmapped],
                value_rules=value_rules,
                confirmed_by=None,
                confidence_summary={m.user_header: {"tier": m.tier, "confidence": m.confidence} for m in result.auto_mapped},
            )

    if needs_review:
        db.add(
            Upload(
                id=upload_id,
                merchant_id=merchant_uuid,
                analyzer_type=analyzer_type,
                data_source=display_source,
                status=UploadStatus.needs_mapping,
            )
        )
        await db.commit()
        return success_response(
            {"upload_id": str(upload_id), "status": UploadStatus.needs_mapping.value, "mapping": result.to_dict()}
        )

    upload = Upload(
        id=upload_id,
        merchant_id=merchant_uuid,
        analyzer_type=analyzer_type,
        data_source=display_source,
        status=UploadStatus.processing,
    )
    db.add(upload)
    await db.commit()

    # 3.7: `value_rules` (including a previously-confirmed date_locale) was
    # resolved above from the saved mapping but never actually forwarded
    # here -- every zero-touch re-upload reusing a saved mapping silently
    # lost it and fell back to the unconfirmed default locale.
    error = await _dispatch_ingestion(db, upload, vertical, resolved_mapping, source, bank_name, value_rules)
    if error is not None:
        return error

    return success_response({"upload_id": str(upload_id), "status": UploadStatus.processing.value})
