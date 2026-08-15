import uuid
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.sql import func

from app.models.auth import Base


class SubscriptionStatus(str, Enum):
    active = "active"
    past_due = "past_due"
    cancelled = "cancelled"
    incomplete = "incomplete"


class Subscription(Base):
    """One row per user (unique on `user_id`) — the durable record of a
    user's paid plan, on top of the simple `User.subscription_tier` column
    that already exists. `User.subscription_tier` remains the single field
    `app.services.entitlements` reads for gating (so no existing gating code
    changes), and is kept in sync with this table by
    `app.services.payments.apply_successful_charge` /
    `handle_subscription_ended` whenever this row's `tier`/`status` changes.

    `provider` records whichever payment gateway actually processed this
    subscription — Paystack is tried first, Flutterwave is an automatic
    fallback if Paystack's API call fails (see `app.services.payments`).
    Column names are provider-agnostic (`provider_*`, not `paystack_*`)
    since either gateway can populate them."""

    __tablename__ = "subscriptions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    provider = Column(String, nullable=False)
    tier = Column(String, nullable=False, default="basic", server_default="basic")
    status = Column(SAEnum(SubscriptionStatus, validate_strings=True), nullable=False)
    provider_customer_code = Column(String, nullable=True)
    provider_subscription_code = Column(String, nullable=True)
    # Paystack-specific: its `/subscription/disable` call requires this
    # `email_token` alongside the subscription code (captured off the
    # `subscription.create` webhook event). Unused by Flutterwave.
    provider_subscription_token = Column(String, nullable=True)
    provider_plan_code = Column(String, nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
