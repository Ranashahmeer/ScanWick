import uuid
from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reconciliation_reports import AnalyzerType, ReconciliationReport


async def record_analysis_run(
    db: AsyncSession,
    merchant_id: uuid.UUID,
    analyzer_type: AnalyzerType,
    *,
    date_range_start: Optional[date] = None,
    date_range_end: Optional[date] = None,
    base_currency: Optional[str] = None,
    records_analyzed: int = 0,
    records_excluded: int = 0,
    exclusion_detail: Optional[list] = None,
    disabled_features: Optional[list] = None,
    contextual_markers_applied: Optional[list] = None,
) -> ReconciliationReport:
    """Writes one reconciliation_reports row per analysis run, per spec:
    "Every analysis run writes a reconciliation record. Every metric on
    every dashboard links back to its analysis_run_id." The table and its
    GET endpoint have existed since 1.2/1.5, but nothing has ever actually
    written to it until now — every dashboard/diagnostic/predictive
    endpoint from here forward should call this and return str(row.id) as
    meta.analysis_run_id, instead of leaving it null.
    """
    report = ReconciliationReport(
        id=uuid.uuid4(),
        merchant_id=merchant_id,
        analyzer_type=analyzer_type,
        date_range_start=date_range_start,
        date_range_end=date_range_end,
        base_currency=base_currency,
        records_analyzed=records_analyzed,
        records_excluded=records_excluded,
        exclusion_detail=exclusion_detail or [],
        disabled_features=disabled_features or [],
        contextual_markers_applied=contextual_markers_applied or [],
    )
    db.add(report)
    await db.commit()
    return report
