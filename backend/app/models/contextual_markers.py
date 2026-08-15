import uuid

from sqlalchemy import Column, Date, DateTime, String, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.sql import func

from app.models.auth import Base
from app.models.reconciliation_reports import AnalyzerType


class ContextualMarker(Base):
    """Shared across all three analyzers. Marks a date range as anomalous;
    any record whose date falls inside gets is_anomalous=TRUE and is excluded
    from model training. start_date/end_date are both inclusive."""

    __tablename__ = "contextual_markers"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id = Column(Uuid, nullable=False, index=True)
    analyzer_type = Column(SAEnum(AnalyzerType, validate_strings=True), nullable=False)
    label = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    created_by = Column(Uuid, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
