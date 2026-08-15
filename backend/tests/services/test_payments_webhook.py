import hashlib
import hmac
import uuid
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from app.config import settings
from app.models import (
    PaymentTransaction,
    PaymentTransactionStatus,
    Subscription,
    SubscriptionStatus,
    User,
)
from app.services import payments


async def _make_user_with_pending_transaction(db_session, *, provider: str, reference: str) -> User:
    user = User(email="owner@example.com", first_name="Ada", last_name="Owner", is_verified=True, subscription_tier="basic")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    db_session.add(
        PaymentTransaction(
            id=uuid.uuid4(),
            user_id=user.id,
            provider=provider,
            provider_reference=reference,
            amount=8990,
            currency="NGN",
            status=PaymentTransactionStatus.pending,
        )
    )
    await db_session.commit()
    return user


# ── Signature verification ──────────────────────────────────────────────────

def test_verify_paystack_signature_accepts_correctly_signed_body(monkeypatch):
    monkeypatch.setattr(settings, "paystack_secret_key", "sk_test_123")
    body = b'{"event":"charge.success"}'
    valid_signature = hmac.new(b"sk_test_123", body, hashlib.sha512).hexdigest()

    assert payments.verify_paystack_signature(body, valid_signature) is True


def test_verify_paystack_signature_rejects_tampered_body(monkeypatch):
    monkeypatch.setattr(settings, "paystack_secret_key", "sk_test_123")
    body = b'{"event":"charge.success"}'
    signature_for_different_body = hmac.new(b"sk_test_123", b'{"event":"other"}', hashlib.sha512).hexdigest()

    assert payments.verify_paystack_signature(body, signature_for_different_body) is False


def test_verify_paystack_signature_rejects_missing_header(monkeypatch):
    monkeypatch.setattr(settings, "paystack_secret_key", "sk_test_123")
    assert payments.verify_paystack_signature(b"{}", None) is False


def test_verify_flutterwave_signature_is_a_direct_compare(monkeypatch):
    monkeypatch.setattr(settings, "flutterwave_webhook_secret_hash", "my-dashboard-secret")

    assert payments.verify_flutterwave_signature("my-dashboard-secret") is True
    assert payments.verify_flutterwave_signature("wrong-value") is False
    assert payments.verify_flutterwave_signature(None) is False


# ── apply_successful_charge ──────────────────────────────────────────────────

async def test_apply_successful_charge_upgrades_user_and_creates_subscription(db_session):
    user = await _make_user_with_pending_transaction(db_session, provider="paystack", reference="ref-success-1")

    await payments.apply_successful_charge(
        db_session,
        reference="ref-success-1",
        provider_name="paystack",
        event_type="charge.success",
        subscription_code="SUB_123",
        subscription_token="tok_abc",
    )

    await db_session.refresh(user)
    assert user.subscription_tier == "premium"

    transaction = (
        await db_session.execute(
            select(PaymentTransaction).where(PaymentTransaction.provider_reference == "ref-success-1")
        )
    ).scalar_one()
    assert transaction.status == PaymentTransactionStatus.success

    subscription = (
        await db_session.execute(select(Subscription).where(Subscription.user_id == user.id))
    ).scalar_one()
    assert subscription.tier == "premium"
    assert subscription.status == SubscriptionStatus.active
    assert subscription.provider_subscription_code == "SUB_123"
    assert subscription.provider_subscription_token == "tok_abc"


async def test_apply_successful_charge_grants_the_tier_the_transaction_was_actually_for(db_session):
    """A Basic checkout must grant Basic, not silently upgrade to Premium —
    apply_successful_charge reads PaymentTransaction.tier rather than
    assuming premium."""
    user = User(email="basic-buyer@example.com", is_verified=True, subscription_tier="free")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    db_session.add(
        PaymentTransaction(
            id=uuid.uuid4(),
            user_id=user.id,
            provider="paystack",
            provider_reference="ref-basic-1",
            tier="basic",
            amount=4500,
            currency="NGN",
            status=PaymentTransactionStatus.pending,
        )
    )
    await db_session.commit()

    await payments.apply_successful_charge(
        db_session, reference="ref-basic-1", provider_name="paystack", event_type="charge.success"
    )

    await db_session.refresh(user)
    assert user.subscription_tier == "basic"
    subscription = (
        await db_session.execute(select(Subscription).where(Subscription.user_id == user.id))
    ).scalar_one()
    assert subscription.tier == "basic"


async def test_apply_successful_charge_is_idempotent_on_repeat_delivery(db_session):
    """Both Paystack and Flutterwave retry webhook delivery on a slow/failed
    response — a second delivery of the same event must not double-apply."""
    user = await _make_user_with_pending_transaction(db_session, provider="paystack", reference="ref-dup")

    await payments.apply_successful_charge(db_session, reference="ref-dup", provider_name="paystack", event_type="charge.success")
    await payments.apply_successful_charge(db_session, reference="ref-dup", provider_name="paystack", event_type="charge.success")

    subscriptions = (
        (await db_session.execute(select(Subscription).where(Subscription.user_id == user.id))).scalars().all()
    )
    assert len(subscriptions) == 1


async def test_handle_subscription_ended_downgrades_user_to_free(db_session):
    user = await _make_user_with_pending_transaction(db_session, provider="paystack", reference="ref-end-1")
    await payments.apply_successful_charge(
        db_session, reference="ref-end-1", provider_name="paystack", event_type="charge.success", subscription_code="SUB_999"
    )

    await payments.handle_subscription_ended(db_session, subscription_code="SUB_999", provider_name="paystack")

    await db_session.refresh(user)
    assert user.subscription_tier == "free"
    subscription = (
        await db_session.execute(select(Subscription).where(Subscription.user_id == user.id))
    ).scalar_one()
    assert subscription.status == SubscriptionStatus.cancelled


async def test_request_cancellation_calls_provider_when_a_real_plan_is_configured(db_session, monkeypatch):
    """Only when a real Paystack Plan / Flutterwave Payment Plan is
    configured (see _has_real_recurring_plan) does cancellation defer to
    the provider — a genuine recurring subscription exists to disable."""
    monkeypatch.setattr("app.config.settings.paystack_premium_plan_code", "PLN_real_plan")

    user = await _make_user_with_pending_transaction(db_session, provider="paystack", reference="ref-cancel-1")
    await payments.apply_successful_charge(
        db_session,
        reference="ref-cancel-1",
        provider_name="paystack",
        event_type="charge.success",
        subscription_code="SUB_555",
        subscription_token="tok_555",
    )

    with patch.object(payments._PRIMARY, "cancel_subscription", new=AsyncMock(return_value=None)) as mock_cancel:
        await payments.request_cancellation(db_session, user)

    mock_cancel.assert_awaited_once_with(subscription_code="SUB_555", subscription_token="tok_555")
    subscription = (
        await db_session.execute(select(Subscription).where(Subscription.user_id == user.id))
    ).scalar_one()
    assert subscription.cancel_at_period_end is True
    # Access isn't revoked immediately -- only once the provider later
    # confirms the period actually ended (handle_subscription_ended).
    assert subscription.tier == "premium"


async def test_request_cancellation_downgrades_immediately_when_no_real_plan_is_configured(db_session):
    """The current reality of this deployment (no Paystack Plan /
    Flutterwave Payment Plan configured for any tier): every charge is a
    one-time purchase, so there is no provider-side subscription to defer
    to — cancelling must downgrade right away rather than promising a
    "cancel at period end" that current_period_end being permanently unset
    would mean never actually resolves."""
    user = await _make_user_with_pending_transaction(db_session, provider="paystack", reference="ref-cancel-2")
    await payments.apply_successful_charge(
        db_session,
        reference="ref-cancel-2",
        provider_name="paystack",
        event_type="charge.success",
        subscription_code="10389692",  # a bare Flutterwave-style transaction id, not a real subscription
    )

    with patch.object(payments._PRIMARY, "cancel_subscription", new=AsyncMock()) as mock_cancel:
        await payments.request_cancellation(db_session, user)

    mock_cancel.assert_not_awaited()
    await db_session.refresh(user)
    assert user.subscription_tier == "free"
    subscription = (
        await db_session.execute(select(Subscription).where(Subscription.user_id == user.id))
    ).scalar_one()
    assert subscription.tier == "free"
    assert subscription.status == SubscriptionStatus.cancelled
