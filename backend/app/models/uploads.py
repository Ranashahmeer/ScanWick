import uuid
from enum import Enum

from sqlalchemy import JSON, Column, Date, DateTime, Integer, String, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.sql import func

from app.models.auth import Base
from app.models.reconciliation_reports import AnalyzerType


class UploadStatus(str, Enum):
    processing = "processing"
    ready = "ready"
    failed = "failed"
    # Set when the Data Mapping Layer (column_mapping.py) can't confidently
    # resolve every column on its own -- ingestion is deliberately NOT
    # dispatched yet in this state; it waits for POST /api/v1/mapping/confirm
    # to move it to `processing`, same as `processing` itself always has.
    needs_mapping = "needs_mapping"


class Upload(Base):
    """Tracks a single file-upload/ingestion batch and its data-quality report.

    Not a table in the spec's documented schema — there's no "uploads" table
    anywhere in the Developer Guide, yet the guide defines
    `GET /api/v1/upload/{upload_id}/quality-report` and `POST /api/v1/upload/csv`
    returning an `upload_id`, which both need somewhere to read/write. This is
    the minimal plumbing for that gap, shared across all three analyzers via
    `analyzer_type` — same pattern as `contextual_markers`/`reconciliation_reports`.
    """

    __tablename__ = "uploads"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id = Column(Uuid, nullable=False, index=True)
    analyzer_type = Column(SAEnum(AnalyzerType), nullable=False)
    data_source = Column(String, nullable=True)
    status = Column(SAEnum(UploadStatus), nullable=False, default=UploadStatus.processing)
    rows_parsed = Column(Integer, nullable=True)
    rows_rejected = Column(Integer, nullable=True)
    date_range_start = Column(Date, nullable=True)
    date_range_end = Column(Date, nullable=True)
    days_of_history = Column(Integer, nullable=True)
    warnings = Column(JSON, nullable=True, default=list)
    # Analyzer-specific quality fields that don't fit the shared columns above
    # (task 1.26: Bank's months_of_data/balance_integrity/date_gaps). Nullable/
    # unused by Ecommerce and Sales uploads.
    analyzer_metadata = Column(JSON, nullable=True)
    # Audit #13: every ingestion path could previously fail with an unhandled
    # exception, leaving `status` stuck at `processing` forever (no code
    # anywhere ever set it to `failed`). Populated alongside status=failed;
    # null otherwise.
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
