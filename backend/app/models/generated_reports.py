import uuid
from enum import Enum

from sqlalchemy import JSON, Column, Date, DateTime, Integer, String, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.sql import func

from app.models.auth import Base


class ReportModule(str, Enum):
    finance = "finance"
    sales = "sales"
    commerce = "commerce"
    cross_module = "cross_module"


class GeneratedReport(Base):
    """One row per report the user has generated (from a library template
    or the custom builder) or a schedule has produced on their behalf —
    backs both the Report Viewer (read by id) and Export History (read as
    a list). `template_key` is null for a custom (non-template) report.
    `stats`/`chart` are the exact shape the frontend renders, computed at
    generation time from real vertical data — never edited after the
    fact, so re-opening an old report always shows what was true when it
    was generated, not today's numbers."""

    __tablename__ = "generated_reports"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id = Column(Uuid, nullable=False, index=True)
    title = Column(String, nullable=False)
    module = Column(SAEnum(ReportModule, validate_strings=True), nullable=False)
    template_key = Column(String, nullable=True, index=True)
    date_range_start = Column(Date, nullable=True)
    date_range_end = Column(Date, nullable=True)
    stats = Column(JSON, nullable=False, default=list)
    chart = Column(JSON, nullable=False, default=list)
    note = Column(String, nullable=True)
    source = Column(String, nullable=True)
    pdf_url = Column(String, nullable=True)
    excel_url = Column(String, nullable=True)
    analysis_run_id = Column(Uuid, nullable=True)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
