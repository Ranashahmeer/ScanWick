import uuid

from sqlalchemy import Boolean, Column, Date, Numeric, String, Uuid, Integer

from app.models.auth import Base


class Account(Base):
    """Canonical bank account row. `account_number_hash` is SHA-256
    (one-way, via `app.services.encryption.hash_value`) — the plain account
    number is never stored here, matching spec exactly. Distinct from the
    legacy `BankAccountIdentifier` table (0.5) used by the old `/api/analyze`
    bank-statement path, which also keeps a reversible Fernet-encrypted copy
    for a different purpose; this table doesn't need that.

    `user_id` is a plain UUID, not an enforced FK — same `users.id` being an
    Integer PK vs. the UUID convention every Phase 1 canonical table uses,
    raised repeatedly already (orders.merchant_id/customer_id in 1.7,
    deals.user_id/rep_id in 1.15, reps_with_data_gaps.rep_name in 1.18).
    """

    __tablename__ = "accounts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, nullable=False, index=True)
    bank_name = Column(String, nullable=True)
    account_number_hash = Column(String, nullable=False, index=True)
    base_currency = Column(String(3), nullable=True)
    statement_period_start = Column(Date, nullable=True)
    statement_period_end = Column(Date, nullable=True)
    opening_balance = Column(Integer, nullable=True)
    closing_balance = Column(Integer, nullable=True)
    computed_closing_balance = Column(Integer, nullable=True)
    balance_integrity_passed = Column(Boolean, nullable=True)
    balance_discrepancy = Column(Integer, nullable=True)
