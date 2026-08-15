import uuid

from sqlalchemy import JSON, Column, DateTime, Integer, String, UniqueConstraint, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.sql import func

from app.models.auth import Base
from app.models.reconciliation_reports import AnalyzerType


class ColumnMapping(Base):
    """A confirmed (or auto-applied) column-header mapping for one merchant's
    recurring upload shape -- the Data Mapping Layer's persistence, per
    docs/Scanwick_Mapping_Layer_Guide.pdf Part 4.1. Looked up by
    (merchant_id, analyzer_type, source_signature) so a future upload with
    the identical header set is zero-touch (see
    app/services/column_mapping.py:compute_source_signature); any header
    change re-triggers confirmation, by design.

    `confirmed_by` is null for a mapping that auto-applied without ever
    needing a user (every field resolved confidently at tier 1/2) -- not
    every row here was actually reviewed by a human."""

    __tablename__ = "column_mappings"
    __table_args__ = (
        UniqueConstraint("merchant_id", "analyzer_type", "source_signature", name="uq_column_mapping_signature"),
    )

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id = Column(Uuid, nullable=False, index=True)
    analyzer_type = Column(SAEnum(AnalyzerType, validate_strings=True), nullable=False)
    source_signature = Column(String, nullable=False, index=True)
    mapping = Column(JSON, nullable=False, default=dict)
    unmapped_headers = Column(JSON, nullable=True, default=list)
    value_rules = Column(JSON, nullable=True, default=dict)
    confirmed_by = Column(Integer, nullable=True)
    confidence_summary = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
