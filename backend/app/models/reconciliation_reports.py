import uuid
from enum import Enum

from sqlalchemy import JSON, Column, Date, DateTime, Integer, String, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.sql import func

from app.models.auth import Base


class AnalyzerType(str, Enum):
    ecommerce = "ecommerce"
    bank = "bank"


class ReconciliationReport(Base):
    """Shared across all three analyzers — id is the `analysis_run_id` returned in
    every API meta object."""

    __tablename__ = "reconciliation_reports"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id = Column(Uuid, nullable=False, index=True)
    analyzer_type = Column(SAEnum(AnalyzerType, validate_strings=True), nullable=False)
    source_file_id = Column(Uuid, nullable=True)
    date_range_start = Column(Date, nullable=True)
    date_range_end = Column(Date, nullable=True)
    base_currency = Column(String(3), nullable=True)
    exchange_rate_source = Column(String, nullable=True)
    records_analyzed = Column(Integer, nullable=True)
    records_excluded = Column(Integer, nullable=True)
    exclusion_detail = Column(JSON, nullable=True, default=list)
    disabled_features = Column(JSON, nullable=True, default=list)
    contextual_markers_applied = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
