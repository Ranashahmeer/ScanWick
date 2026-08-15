import uuid
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, String, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.sql import func

from app.models.auth import Base


class ReportFrequency(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"


class ReportFormat(str, Enum):
    pdf = "pdf"
    excel = "excel"


class ReportSchedule(Base):
    """A recurring report the merchant wants generated and emailed
    automatically (Scheduled Reports tab) — dispatched by the
    `reports.run_scheduled_reports` Celery beat task, same pattern as
    `generate-postmortem-reports`. `template_key` must be a library
    template (schedules aren't defined for one-off custom reports, since
    there'd be nothing repeatable to re-run)."""

    __tablename__ = "report_schedules"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id = Column(Uuid, nullable=False, index=True)
    template_key = Column(String, nullable=False)
    frequency = Column(SAEnum(ReportFrequency, validate_strings=True), nullable=False)
    recipients = Column(String, nullable=False)
    format = Column(SAEnum(ReportFormat, validate_strings=True), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
