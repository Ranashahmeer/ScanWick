import uuid
from enum import Enum

from sqlalchemy import Column, DateTime, Integer, String, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.sql import func

from app.models.auth import Base


class LoginEventResult(str, Enum):
    success = "success"
    blocked = "blocked"


class LoginEvent(Base):
    """One row per login attempt against a known account — backs the Login &
    Security tab's "Login history" table, which previously rendered a
    hardcoded fake array. `user_id` is a plain Integer with no FK (same
    convention as RefreshToken.user_id) rather than a relationship, since
    nothing here ever needs to join back through the ORM.

    Attempts against an unrecognized email are never logged here (same
    anti-enumeration reasoning already used in app/routes/auth.py's
    resend-otp route) — only attempts where a user row was actually found."""

    __tablename__ = "login_events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, nullable=False, index=True)
    result = Column(SAEnum(LoginEventResult, validate_strings=True), nullable=False)
    reason = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
