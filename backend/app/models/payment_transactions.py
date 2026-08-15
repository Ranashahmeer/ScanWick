import uuid
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.sql import func

from app.models.auth import Base


class PaymentTransactionStatus(str, Enum):
    pending = "pending"
    success = "success"
    failed = "failed"


class PaymentTransaction(Base):
    """Append-only audit log of every checkout attempt — powers the billing-
    history table on the frontend and, more importantly, is the idempotency
    key for webhook processing: `provider_reference` is unique, so a webhook
    delivered twice for the same charge (Paystack/Flutterwave both retry on
    a slow/failed response) can never double-apply. `provider` + `status`
    together record exactly which gateway processed this specific charge and
    what happened, independent of whatever the user's current `Subscription`
    row says (a user could in principle have transactions from both
    providers over time, if Paystack was down for one checkout)."""

    __tablename__ = "payment_transactions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subscription_id = Column(Uuid, ForeignKey("subscriptions.id"), nullable=True)
    provider = Column(String, nullable=False)
    provider_reference = Column(String, nullable=False, unique=True, index=True)
    # "basic" | "premium" — which paid tier this specific charge was for.
    # apply_successful_charge() reads this to know what to actually grant
    # once a charge succeeds, rather than assuming premium.
    tier = Column(String, nullable=True)
    amount = Column(Integer, nullable=False)
    currency = Column(String, nullable=False, default="NGN", server_default="NGN")
    status = Column(SAEnum(PaymentTransactionStatus, validate_strings=True), nullable=False)
    provider_event_type = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
