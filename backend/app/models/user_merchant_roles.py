import uuid
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.sql import func

from app.models.auth import Base


class Vertical(str, Enum):
    ecommerce = "ecommerce"
    bank = "bank"


class EcommerceRole(str, Enum):
    owner = "owner"
    admin = "admin"
    manager = "manager"
    viewer = "viewer"


class BankRole(str, Enum):
    bank_owner = "bank_owner"
    bank_admin = "bank_admin"
    loan_officer = "loan_officer"
    bank_viewer = "bank_viewer"


class UserMerchantRole(Base):
    """One row per (user, merchant, vertical) — the foundational RBAC
    schema added for 5.1/5.2 (none existed before: `User` had no role
    field, no merchant_id, and the JWT carries only user_id/email).
    `role` is a plain string rather than a single shared enum because
    each vertical has its own distinct role set (EcommerceRole vs
    BankRole) — validated against the right enum at the service layer
    based on `vertical`, not DB-enforced. For vertical=bank (5.3),
    `merchant_id` stores `Account.user_id` (the business owner who owns
    the bank account) — the same UUID space as Ecommerce's merchant_id,
    not a separate per-account scope, since one business can have
    multiple bank accounts under one set of bank-vertical roles. `rep_id`
    is unused now that the sales vertical (its only consumer) has been
    removed — kept nullable rather than dropped, since removing a column
    is a real migration, not a Section-4-scope model edit.

    `granted_via_invite` distinguishes a role created by
    `team_management.accept_invite()` (always for someone ELSE's merchant)
    from a role created by `merchant_provisioning.ensure_merchant_provisioned()`
    or seeded directly (the user's own merchant, or legacy data predating
    the invite feature). `ensure_merchant_provisioned` reads this flag to
    decide whether it's safe to auto-backfill owner-tier roles for any
    vertical missing on this merchant_id — never for an invited role, always
    for an own/legacy one. Defaults False so existing rows are unaffected."""

    __tablename__ = "user_merchant_roles"
    __table_args__ = (UniqueConstraint("user_id", "merchant_id", "vertical", name="uq_user_merchant_vertical"),)

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    merchant_id = Column(Uuid, nullable=False, index=True)
    vertical = Column(SAEnum(Vertical, validate_strings=True), nullable=False)
    role = Column(String, nullable=False)
    rep_id = Column(Uuid, nullable=True)
    granted_via_invite = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
