import uuid
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.sql import func

from app.models.auth import Base
from app.models.user_merchant_roles import Vertical


class TeamInviteStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    revoked = "revoked"
    expired = "expired"


class TeamInvite(Base):
    """An outstanding (or resolved) invitation for `email` to join
    `merchant_id` with a specific `vertical`/`role`. Only the merchant's
    primary owner (`merchant_provisioning.is_primary_owner`) can create,
    resend, or revoke one — see `app.services.team_management`.

    `role` is validated against the right per-vertical enum
    (EcommerceRole/BankRole) at the service layer, same convention
    as `UserMerchantRole.role`. `rep_id` is unused now that the sales
    vertical (its only consumer) has been removed.

    `token` is the single-use credential in the invite email's link
    (`secrets.token_urlsafe(32)`, the same primitive `forgot_password`
    already uses for its reset link)."""

    __tablename__ = "team_invites"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id = Column(Uuid, nullable=False, index=True)
    invited_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    email = Column(String, nullable=False, index=True)
    vertical = Column(SAEnum(Vertical, validate_strings=True), nullable=False)
    role = Column(String, nullable=False)
    rep_id = Column(Uuid, nullable=True)
    token = Column(String, nullable=False, unique=True, index=True)
    status = Column(SAEnum(TeamInviteStatus, validate_strings=True), nullable=False, default=TeamInviteStatus.pending)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
