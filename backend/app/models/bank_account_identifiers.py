from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.models.auth import Base


class BankAccountIdentifier(Base):
    """Records which bank accounts a user has uploaded statements for.

    The raw account number is never stored: account_number_hash (SHA-256, one-way)
    backs matching/dedup, and account_number_encrypted (Fernet, reversible) is
    kept only for the rare case the actual number needs to be read back.

    Tied to user_id (Integer, matching the legacy auth User table) rather than
    the UUID merchant_id used by the newer Phase 1 canonical tables — there is
    no merchant/tenant concept wired into auth yet. Revisit this FK target when
    task 1.20 builds the real accounts/bank_transactions tables.
    """

    __tablename__ = "bank_account_identifiers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    account_number_hash = Column(String, nullable=False, index=True)
    account_number_encrypted = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "account_number_hash", name="uq_user_account_hash"),
    )
