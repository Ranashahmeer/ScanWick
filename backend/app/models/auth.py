from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    google_id = Column(String, unique=True, nullable=True)
    avatar_url = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    # "free" | "basic" | "premium" -- task 5.6, expanded to a real 3-tier
    # model once Basic became a genuinely separate paid plan (not just the
    # unpaid default). A plain column directly on User (not exclusively a
    # separate Subscription table) since app.services.entitlements only
    # needs a fast, always-current feature-access check; app.models.Subscription
    # holds the fuller billing lifecycle and keeps this column in sync
    # (see app.services.payments).
    subscription_tier = Column(String, nullable=False, default="free", server_default="free")
    # Account & Billing > Account tab profile fields — free-text (not FK'd
    # lookups) since there's no company/currency/timezone reference table
    # anywhere else in the schema; matches how the frontend form already
    # treats them (plain text inputs, not selects).
    company = Column(String, nullable=True)
    company_size = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    primary_currency = Column(String, nullable=True)
    language = Column(String, nullable=True)
    timezone = Column(String, nullable=True)
    # TOTP 2FA (Login & Security tab). `totp_secret` is stored via
    # app.services.encryption.encrypt_field — never persisted in the clear.
    # Set (not yet trusted) as soon as /2fa/setup is called; only
    # `totp_enabled` gates login, so an abandoned setup never locks anyone out.
    totp_secret = Column(String, nullable=True)
    totp_enabled = Column(Boolean, nullable=False, default=False, server_default="false")
    # Privacy & Data "Delete account" — set by POST /auth/delete-account,
    # cleared by POST /auth/delete-account/cancel. Deliberately not enforced
    # anywhere yet (no scheduled purge job) — see app/routes/privacy.py plan.
    deletion_requested_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    # Populated at issue/refresh time (app/routes/auth.py's _issue_tokens) —
    # the only thing backing the Login & Security "Active sessions" list,
    # which previously rendered a hardcoded fake array.
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class OtpRecord(Base):
    __tablename__ = "otp_records"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    code = Column(String, nullable=False)
    # purpose: "verification" | "login" | "password_reset"
    purpose = Column(String, nullable=False, default="verification")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
