"""Subscription billing business logic: checkout (with automatic Paystack
-> Flutterwave fallback), webhook processing, and cancellation. Every
function here is provider-agnostic once it has a `PaymentProvider` in hand —
see `app.services.payment_provider` for the interface both `PaystackProvider`
and `FlutterwaveProvider` implement.

`User.subscription_tier` (the pre-existing column `app.services.entitlements`
already gates on) is kept in sync by `apply_successful_charge` /
`handle_subscription_ended` below — this is the only code that ever writes
to it now, but its shape and every existing reader are untouched.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import uuid
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery_app
from app.config import settings
from app.database import async_session
from app.models import PaymentTransaction, PaymentTransactionStatus, Subscription, SubscriptionStatus, User
from app.services import fx_rates
from app.services.entitlements import BASIC_TIER, FREE_TIER, PREMIUM_TIER
from app.services.flutterwave_client import FlutterwaveProvider
from app.services.payment_provider import CheckoutResult, PaymentProvider
from app.services.paystack_client import PaystackAPIError, PaystackProvider

logger = logging.getLogger("app.payments")

_PRIMARY: PaymentProvider = PaystackProvider()
_FALLBACK: PaymentProvider = FlutterwaveProvider()
_PROVIDERS_BY_NAME: dict[str, PaymentProvider] = {_PRIMARY.name: _PRIMARY, _FALLBACK.name: _FALLBACK}

# Each paid tier's fixed USD price and provider plan-code settings, keyed by
# tier so initiate_checkout doesn't need a chain of if/elif per tier — add a
# new paid tier by adding one entry here (plus its config.py settings).
_PRICE_USD_BY_TIER = {
    BASIC_TIER: lambda: settings.basic_plan_price_usd,
    PREMIUM_TIER: lambda: settings.premium_plan_price_usd,
}
_PAYSTACK_PLAN_CODE_BY_TIER = {
    BASIC_TIER: lambda: settings.paystack_basic_plan_code,
    PREMIUM_TIER: lambda: settings.paystack_premium_plan_code,
}
_FLUTTERWAVE_PLAN_ID_BY_TIER = {
    BASIC_TIER: lambda: settings.flutterwave_basic_plan_id,
    PREMIUM_TIER: lambda: settings.flutterwave_premium_plan_id,
}


def _plan_code_for_tier(tier: str, provider: PaymentProvider) -> Optional[str]:
    lookup = _PAYSTACK_PLAN_CODE_BY_TIER if provider.name == "paystack" else _FLUTTERWAVE_PLAN_ID_BY_TIER
    value = lookup[tier]()
    return value or None


def _has_real_recurring_plan(provider_name: str, tier: str) -> bool:
    """True only if a real Paystack Plan / Flutterwave Payment Plan is
    configured for this provider+tier — i.e. the checkout that created this
    subscription was a genuine recurring plan, not a one-time charge. Until
    real plan codes are configured (see config.py), every checkout is a
    one-time charge with no provider-side subscription object to cancel —
    request_cancellation below uses this to behave honestly about that
    instead of pretending a deferred "cancel at period end" will ever
    resolve, which it can't: current_period_end is never populated without
    a real plan, so the webhook that would complete a deferred cancellation
    would never arrive."""
    return _plan_code_for_tier(tier, _PROVIDERS_BY_NAME[provider_name]) is not None


async def _price_kobo_for_tier(db: AsyncSession, tier: str) -> int:
    """Each tier's price is fixed in USD (config.py) — this converts that
    fixed price to NGN kobo at the live rate (app.services.fx_rates),
    refreshed hourly, rather than charging a stale hardcoded NGN figure.
    Paystack/Flutterwave both settle in NGN in this app; USD is never the
    actual settlement currency, only the reference price. Decimal
    throughout, not float — `rate` is already a Decimal (from the DB/API),
    and money math shouldn't go through float at all."""
    usd_price = Decimal(str(_PRICE_USD_BY_TIER[tier]()))
    rate = await fx_rates.get_current_usd_ngn_rate(db)
    kobo = usd_price * rate * 100
    return int(kobo.to_integral_value(rounding=ROUND_HALF_UP))


# ── Checkout ─────────────────────────────────────────────────────────────────

async def initiate_checkout(db: AsyncSession, user: User, tier: str) -> CheckoutResult:
    """Starts a hosted-checkout transaction, trying Paystack first and
    transparently falling back to Flutterwave if Paystack's API call fails
    (bad credentials, an outage, or simply not configured) — the caller
    never sees the difference, they just get an `authorization_url` to
    redirect the browser to. `tier` must be a paid tier (`basic` or
    `premium`) — Free needs no checkout at all."""
    if tier not in _PRICE_USD_BY_TIER:
        raise ValueError(f"'{tier}' has no price — only {sorted(_PRICE_USD_BY_TIER)} can be checked out.")

    price_kobo = await _price_kobo_for_tier(db, tier)
    callback_url = f"{settings.frontend_url}/account?tab=billing"
    metadata = {"user_id": user.id, "tier": tier}

    try:
        result = await _PRIMARY.initialize_transaction(
            email=user.email,
            amount_kobo=price_kobo,
            callback_url=callback_url,
            metadata=metadata,
            plan_code=_plan_code_for_tier(tier, _PRIMARY),
        )
        provider = _PRIMARY
    except PaystackAPIError as exc:
        logger.warning("Paystack checkout failed for user %s (%s) — falling back to Flutterwave", user.id, exc)
        result = await _FALLBACK.initialize_transaction(
            email=user.email,
            amount_kobo=price_kobo,
            callback_url=callback_url,
            metadata=metadata,
            plan_code=_plan_code_for_tier(tier, _FALLBACK),
        )
        provider = _FALLBACK

    db.add(
        PaymentTransaction(
            id=uuid.uuid4(),
            user_id=user.id,
            provider=provider.name,
            provider_reference=result.reference,
            tier=tier,
            amount=Decimal(price_kobo) / 100,
            currency="NGN",
            status=PaymentTransactionStatus.pending,
        )
    )
    await db.commit()
    return result


async def verify_and_apply(db: AsyncSession, reference: str, user_id: int) -> str:
    """Used by `GET /verify/{reference}` right after the browser redirects
    back from checkout, so the frontend can show "Premium active" without
    waiting on the webhook. Looks up which provider actually processed this
    reference, asks that provider directly, and — on success — runs the
    exact same `apply_successful_charge` the webhook path uses, so the two
    can never disagree about what a successful charge means. Returns the
    resulting status: "success" / "pending" / "failed".

    `user_id` must match the transaction's owner — without this check any
    authenticated user could poke any other user's payment reference (low
    practical risk since references are unguessable UUIDs, but this is a
    financial endpoint and the check is nearly free)."""
    transaction = (
        await db.execute(select(PaymentTransaction).where(PaymentTransaction.provider_reference == reference))
    ).scalar_one_or_none()
    if transaction is None or transaction.user_id != user_id:
        raise ValueError(f"No payment transaction found for reference {reference!r}.")

    provider = _PROVIDERS_BY_NAME[transaction.provider]
    result = await provider.verify_transaction(reference)

    if result.status == "success":
        await apply_successful_charge(
            db,
            reference=reference,
            provider_name=transaction.provider,
            event_type="manual_verify",
            subscription_code=result.subscription_code,
            current_period_end=result.current_period_end,
        )
    elif result.status == "failed" and transaction.status == PaymentTransactionStatus.pending:
        transaction.status = PaymentTransactionStatus.failed
        await db.commit()

    return result.status


# ── Shared state transitions (called by both webhooks and verify_and_apply) ──

async def apply_successful_charge(
    db: AsyncSession,
    *,
    reference: str,
    provider_name: str,
    event_type: Optional[str] = None,
    subscription_code: Optional[str] = None,
    subscription_token: Optional[str] = None,
    current_period_end: Optional[datetime] = None,
) -> None:
    """The single idempotent handler for "a charge succeeded" — used by both
    webhook routes and the manual verify endpoint. Safe to call twice for
    the same reference (a retried webhook delivery, or a webhook landing
    just after a manual verify already applied it): the second call is a
    no-op, since `PaymentTransaction.provider_reference` is unique and its
    `status` only ever moves pending -> success once.

    Also safe if a webhook and a manual verify race for the very first
    application of the same reference: both could see "no Subscription row
    yet" and both try to create one, which would violate
    `Subscription.user_id`'s unique constraint — caught below and retried
    against whichever row actually won, same rollback-and-refetch pattern
    `merchant_provisioning.ensure_merchant_provisioned` already uses for
    the equivalent race there."""
    async def _apply(*, allow_create_subscription: bool) -> Optional[bool]:
        """Returns True if it applied the charge, False if it found nothing
        to do (already success), or None if a fresh Subscription needs
        creating but the caller isn't allowed to do that on this pass
        (signals the retry-without-create path below)."""
        transaction = (
            await db.execute(select(PaymentTransaction).where(PaymentTransaction.provider_reference == reference))
        ).scalar_one_or_none()
        if transaction is None:
            logger.warning("apply_successful_charge: no PaymentTransaction found for reference %s", reference)
            return False
        if transaction.status == PaymentTransactionStatus.success:
            return False

        # Which tier this charge actually grants — set on the transaction
        # back in initiate_checkout(), never guessed here. Falls back to
        # premium only for a transaction created before `tier` existed on
        # this table (pre-migration rows, if any).
        granted_tier = transaction.tier or PREMIUM_TIER

        subscription = (
            await db.execute(select(Subscription).where(Subscription.user_id == transaction.user_id))
        ).scalar_one_or_none()
        if subscription is None:
            if not allow_create_subscription:
                return None
            subscription = Subscription(
                id=uuid.uuid4(), user_id=transaction.user_id, provider=provider_name, status=SubscriptionStatus.active
            )
            db.add(subscription)

        transaction.status = PaymentTransactionStatus.success
        transaction.provider_event_type = event_type

        subscription.provider = provider_name
        subscription.tier = granted_tier
        subscription.status = SubscriptionStatus.active
        subscription.cancel_at_period_end = False
        if subscription_code:
            subscription.provider_subscription_code = subscription_code
        if subscription_token:
            subscription.provider_subscription_token = subscription_token
        if current_period_end:
            subscription.current_period_end = current_period_end

        transaction.subscription_id = subscription.id

        # This is the one line that keeps app.services.entitlements' gating
        # (which reads User.subscription_tier directly) working unmodified.
        user = (await db.execute(select(User).where(User.id == transaction.user_id))).scalar_one_or_none()
        if user is not None:
            user.subscription_tier = granted_tier
        return True

    # allow_create_subscription=True here always returns True/False, never
    # None (only a retry with allow_create_subscription=False can) — this
    # first pass just needs "was there anything to apply at all".
    if not await _apply(allow_create_subscription=True):
        return

    try:
        await db.commit()
    except IntegrityError:
        # A concurrent call (webhook racing a manual verify, or two webhook
        # deliveries close together) already created the Subscription row
        # for this user in between our SELECT and commit — same class of
        # race `merchant_provisioning.ensure_merchant_provisioned` already
        # handles via rollback-and-refetch. Retry against whichever row
        # actually won instead of erroring out.
        await db.rollback()
        if await _apply(allow_create_subscription=False):
            await db.commit()
        else:
            logger.warning(
                "apply_successful_charge: retry after IntegrityError found nothing to apply for reference %s "
                "— unexpected, investigate.",
                reference,
            )


async def handle_subscription_ended(db: AsyncSession, *, subscription_code: str, provider_name: str) -> None:
    """Called once a provider confirms a subscription's billing period truly
    ended without renewing (either the user cancelled and the period ran
    out, or a renewal charge kept failing) — downgrades the user back to
    the real free tier (not partway down to Basic, regardless of which paid
    tier they were on — a straight cancel-to-Basic downgrade isn't
    supported, see request_cancellation's docstring). Cancelling
    (`request_cancellation` below) does NOT call this directly: the user
    keeps their paid tier's access until the provider confirms the period
    actually ended, which is what this function reacts to."""
    subscription = (
        await db.execute(
            select(Subscription).where(
                Subscription.provider_subscription_code == subscription_code,
                Subscription.provider == provider_name,
            )
        )
    ).scalar_one_or_none()
    if subscription is None:
        logger.warning(
            "handle_subscription_ended: no Subscription found for %s/%s", provider_name, subscription_code
        )
        return

    subscription.status = SubscriptionStatus.cancelled
    subscription.tier = FREE_TIER

    user = (await db.execute(select(User).where(User.id == subscription.user_id))).scalar_one_or_none()
    if user is not None:
        user.subscription_tier = FREE_TIER

    await db.commit()


async def request_cancellation(db: AsyncSession, user: User) -> None:
    """Two genuinely different cases, depending on whether a real Paystack
    Plan / Flutterwave Payment Plan is configured for this subscription's
    provider+tier (see _has_real_recurring_plan):

    - A real recurring plan exists: standard SaaS "cancel now, lose access
      at period end" — the user keeps access until the provider confirms
      the billing period actually ended (via handle_subscription_ended,
      above), which arrives as a webhook on its own schedule.
    - No real plan is configured (the current state of this deployment —
      every checkout today is a one-time charge): there is no provider-side
      subscription object to cancel at all, and `current_period_end` is
      never populated without one, so a deferred "cancel at period end"
      would never actually resolve — nothing would ever downgrade the
      user. Cancelling here downgrades immediately instead of promising
      something the system can't keep.

    Either way, cancelling always ends at the Free tier, even for a Basic
    subscriber — there's no "downgrade from Premium straight to Basic"
    path; that would need a fresh Basic checkout instead."""
    subscription = (
        await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    ).scalar_one_or_none()
    if subscription is None or subscription.status != SubscriptionStatus.active:
        raise ValueError("No active subscription to cancel.")

    if not _has_real_recurring_plan(subscription.provider, subscription.tier):
        subscription.status = SubscriptionStatus.cancelled
        subscription.tier = FREE_TIER
        user.subscription_tier = FREE_TIER
        await db.commit()
        return

    provider = _PROVIDERS_BY_NAME[subscription.provider]
    await provider.cancel_subscription(
        subscription_code=subscription.provider_subscription_code,
        subscription_token=subscription.provider_subscription_token,
    )
    subscription.cancel_at_period_end = True
    await db.commit()


# ── Webhook signature verification ──────────────────────────────────────────

def verify_paystack_signature(raw_body: bytes, signature_header: Optional[str]) -> bool:
    """Paystack has no separate webhook secret — you HMAC-SHA512 the raw
    request body with your own API secret key and compare against the
    `x-paystack-signature` header."""
    if not signature_header or not settings.paystack_secret_key:
        return False
    computed = hmac.new(settings.paystack_secret_key.encode(), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(computed, signature_header)


def verify_flutterwave_signature(signature_header: Optional[str]) -> bool:
    """Flutterwave has no HMAC scheme at all — you configure an arbitrary
    secret string in their dashboard and they echo it back verbatim in the
    `verif-hash` header on every call; verification is a direct compare."""
    if not signature_header or not settings.flutterwave_webhook_secret_hash:
        return False
    return hmac.compare_digest(signature_header, settings.flutterwave_webhook_secret_hash)


# ── Webhook event handling ───────────────────────────────────────────────────

async def _handle_paystack_event(db: AsyncSession, event: dict) -> None:
    event_type = event.get("event")
    data = event.get("data") or {}

    if event_type == "charge.success":
        subscription = data.get("subscription") or {}
        await apply_successful_charge(
            db,
            reference=data.get("reference"),
            provider_name="paystack",
            event_type=event_type,
            subscription_code=subscription.get("subscription_code"),
            subscription_token=subscription.get("email_token"),
        )
    elif event_type == "subscription.create":
        # Captures the email_token cancellation needs later, even if
        # charge.success already ran first — event delivery order isn't
        # guaranteed. Only updates an existing Subscription row, never
        # creates one: charge.success (proof of payment) is what does that.
        subscription_code = data.get("subscription_code")
        email_token = data.get("email_token")
        if subscription_code and email_token:
            subscription = (
                await db.execute(
                    select(Subscription).where(Subscription.provider_subscription_code == subscription_code)
                )
            ).scalar_one_or_none()
            if subscription is not None:
                subscription.provider_subscription_token = email_token
                await db.commit()
    elif event_type in ("subscription.disable", "subscription.not_renew"):
        subscription_code = data.get("subscription_code")
        if subscription_code:
            await handle_subscription_ended(db, subscription_code=subscription_code, provider_name="paystack")
    elif event_type == "invoice.payment_failed":
        subscription_code = (data.get("subscription") or {}).get("subscription_code")
        if subscription_code:
            subscription = (
                await db.execute(
                    select(Subscription).where(Subscription.provider_subscription_code == subscription_code)
                )
            ).scalar_one_or_none()
            if subscription is not None:
                subscription.status = SubscriptionStatus.past_due
                await db.commit()
    else:
        logger.info("Unhandled Paystack webhook event: %s", event_type)


async def _handle_flutterwave_event(db: AsyncSession, event: dict) -> None:
    event_type = event.get("event")
    data = event.get("data") or {}

    if event_type == "charge.completed" and data.get("status") == "successful":
        subscription_id = str(data["id"]) if data.get("id") is not None else None
        await apply_successful_charge(
            db,
            reference=data.get("tx_ref"),
            provider_name="flutterwave",
            event_type=event_type,
            subscription_code=subscription_id,
        )
    elif event_type == "subscription.cancelled":
        subscription_id = str(data["id"]) if data.get("id") is not None else None
        if subscription_id:
            await handle_subscription_ended(db, subscription_code=subscription_id, provider_name="flutterwave")
    else:
        logger.info("Unhandled Flutterwave webhook event: %s", event_type)


# ── Celery tasks ─────────────────────────────────────────────────────────────
# Same asyncio.run(...) + own-async_session() wrapper pattern as
# app/services/bank_ingestion.py's ingest_bank_csv task. The webhook routes
# verify the signature synchronously (cheap) then dispatch here and return
# 200 immediately, so a slow DB write never risks the provider timing out
# and retrying the same event unnecessarily.

@celery_app.task(name="payments.process_webhook_event_paystack")
def process_paystack_webhook_task(payload: dict) -> dict:
    return asyncio.run(_process_paystack_webhook_async(payload))


async def _process_paystack_webhook_async(payload: dict) -> dict:
    async with async_session() as db:
        await _handle_paystack_event(db, payload)
    return {"processed": True}


@celery_app.task(name="payments.process_webhook_event_flutterwave")
def process_flutterwave_webhook_task(payload: dict) -> dict:
    return asyncio.run(_process_flutterwave_webhook_async(payload))


async def _process_flutterwave_webhook_async(payload: dict) -> dict:
    async with async_session() as db:
        await _handle_flutterwave_event(db, payload)
    return {"processed": True}
