from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.auth import User
from app.models.reconciliation_reports import ReconciliationReport
from app.models.user_merchant_roles import Vertical
from app.schemas.envelope import error_response, success_response
from app.services.rbac import check_any_role

router = APIRouter(prefix="/api/v1/reconciliation", tags=["reconciliation"])


def _serialize(report: ReconciliationReport) -> dict:
    return {
        "id": str(report.id),
        "merchant_id": str(report.merchant_id),
        "analyzer_type": report.analyzer_type.value,
        "source_file_id": str(report.source_file_id) if report.source_file_id else None,
        "date_range_start": report.date_range_start.isoformat() if report.date_range_start else None,
        "date_range_end": report.date_range_end.isoformat() if report.date_range_end else None,
        "base_currency": report.base_currency,
        "exchange_rate_source": report.exchange_rate_source,
        "records_analyzed": report.records_analyzed,
        "records_excluded": report.records_excluded,
        "exclusion_detail": report.exclusion_detail or [],
        "disabled_features": report.disabled_features or [],
        "contextual_markers_applied": report.contextual_markers_applied or [],
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


@router.get("/{analysis_run_id}")
async def get_reconciliation_report(
    analysis_run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Task 5.4: every role with any read access at all — including the
    spec's "Analyst" (no exact role of that name exists anywhere in this
    build's access tables, since no spec defining it exists in the repo;
    treated as covered by any granted role, since none of
    EcommerceRole/BankRole are write-only) — can reach this.
    Access is keyed off the report's own `merchant_id` + `analyzer_type`
    (mapped 1:1 to `Vertical`), not a query param, since this route only
    ever takes `analysis_run_id`."""
    try:
        run_id = UUID(analysis_run_id)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content=error_response("INVALID_ANALYSIS_RUN_ID", f"'{analysis_run_id}' is not a valid UUID."),
        )

    result = await db.execute(select(ReconciliationReport).where(ReconciliationReport.id == run_id))
    report = result.scalar_one_or_none()

    if report is None:
        return JSONResponse(
            status_code=404,
            content=error_response(
                "RECONCILIATION_NOT_FOUND",
                f"No reconciliation report found for analysis_run_id {analysis_run_id}.",
            ),
        )

    error, _ = await check_any_role(db, current_user, report.merchant_id, Vertical(report.analyzer_type.value))
    if error is not None:
        return error

    return success_response(_serialize(report), analysis_run_id=str(report.id))
