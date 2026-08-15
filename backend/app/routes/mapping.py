import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.database import get_db
from app.dependencies import get_current_user
from app.models import AnalyzerType, Upload, UploadStatus, User, Vertical
from app.routes.uploads import _INGEST_ROLES, _dispatch_ingestion
from app.schemas.envelope import error_response, success_response
from app.services.column_mapping import compute_source_signature, resolve_mapping
from app.services.column_mapping_store import upsert_mapping
from app.services.rbac import check_role
from app.services.upload_staging import read_staged_upload

router = APIRouter(prefix="/api/v1/mapping", tags=["mapping"])
logger = logging.getLogger(__name__)


class ConfirmMappingRequest(BaseModel):
    upload_id: str
    mapping: dict[str, str]
    value_rules: dict = {}


async def _load_upload_for_mapping(db: AsyncSession, upload_id: str, current_user: User):
    """Shared by /detect and /confirm: looks up the Upload row and validates
    the caller against ITS OWN merchant_id/analyzer_type -- never a client-
    resupplied merchant_id -- so a caller can't attribute another merchant's
    staged file to themselves by guessing/reusing an upload_id. Returns
    (error_response_or_None, upload_or_None)."""
    try:
        uid = UUID(upload_id)
    except ValueError:
        return (
            JSONResponse(status_code=400, content=error_response("INVALID_UPLOAD_ID", f"'{upload_id}' is not a valid UUID.")),
            None,
        )

    upload = (await db.execute(select(Upload).where(Upload.id == uid))).scalar_one_or_none()
    if upload is None:
        return (
            JSONResponse(status_code=404, content=error_response("UPLOAD_NOT_FOUND", f"No upload found for upload_id {upload_id}.")),
            None,
        )

    vertical = Vertical(upload.analyzer_type.value)
    error, _ = await check_role(db, current_user, upload.merchant_id, vertical, _INGEST_ROLES[vertical])
    if error is not None:
        return error, None

    if upload.status != UploadStatus.needs_mapping:
        return (
            JSONResponse(
                status_code=409,
                content=error_response(
                    "NOT_AWAITING_MAPPING", f"Upload {upload_id} is not awaiting a column mapping (status: {upload.status.value})."
                ),
            ),
            None,
        )
    return None, upload


@router.post("/detect")
async def detect_mapping(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-runs column detection against an already-staged upload -- mainly a
    "re-check"/retry convenience for the mapping-review screen; the primary
    flow already gets this inline from POST /api/v1/upload/csv's response
    when a mapping needs confirmation."""
    upload_id = body.get("upload_id", "")
    error, upload = await _load_upload_for_mapping(db, upload_id, current_user)
    if error is not None:
        return error

    df = await run_in_threadpool(read_staged_upload, str(upload.id))
    result = resolve_mapping(list(df.columns), upload.analyzer_type)
    return success_response({"upload_id": str(upload.id), "mapping": result.to_dict()})


@router.post("/confirm")
async def confirm_mapping(
    body: ConfirmMappingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Persists the user's confirmed mapping (a ColumnMapping row,
    confirmed_by=current_user.id, upserted on the (merchant_id,
    analyzer_type, source_signature) unique constraint so a later identical
    upload reuses it zero-touch) and dispatches the ingestion Celery task via
    the same _dispatch_ingestion helper the auto-apply fast path in POST
    /upload/csv uses."""
    error, upload = await _load_upload_for_mapping(db, body.upload_id, current_user)
    if error is not None:
        return error

    df = await run_in_threadpool(read_staged_upload, str(upload.id))
    signature = compute_source_signature(list(df.columns), upload.analyzer_type)

    await upsert_mapping(
        db,
        merchant_id=upload.merchant_id,
        analyzer_type=upload.analyzer_type,
        source_signature=signature,
        mapping=body.mapping,
        unmapped_headers=[col for col in df.columns if col not in body.mapping],
        value_rules=body.value_rules,
        confirmed_by=current_user.id,
        confidence_summary={"user_confirmed": True},
    )

    vertical = Vertical(upload.analyzer_type.value)
    # data_source doubles as the source/bank_name slot staged by POST /csv
    # (see routes/uploads.py's upload_csv) -- re-split it back out here.
    source = None if vertical == Vertical.bank else upload.data_source
    bank_name = upload.data_source if vertical == Vertical.bank else None

    error = await _dispatch_ingestion(db, upload, vertical, body.mapping, source, bank_name, body.value_rules)
    if error is not None:
        return error

    return success_response({"upload_id": str(upload.id), "status": UploadStatus.processing.value})
