"""The one interface `app.services.payments` codes against — neither the
routes nor the subscription/webhook business logic ever branch on "which
gateway", they only ever talk to a `PaymentProvider`. `paystack_client.py`
and `flutterwave_client.py` each implement this by wrapping their own raw
HTTP API and mapping its response into the shapes defined here.

Paystack is tried first; Flutterwave is an automatic fallback if Paystack's
call fails (see `payments.initiate_checkout`) — that fallback only works
cleanly because both providers are interchangeable at this interface.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol


@dataclass
class CheckoutResult:
    """What a successful `initialize_transaction` call returns, regardless
    of provider. `authorization_url` is the hosted checkout page the
    frontend redirects the browser to; `reference` is this provider's own
    transaction reference — stored on `PaymentTransaction.provider_reference`
    and used later to verify the charge and to route webhook events."""

    authorization_url: str
    reference: str


@dataclass
class VerifyResult:
    """What a successful `verify_transaction` call returns, regardless of
    provider. `status` is normalized to `"success"` / `"failed"` /
    `"pending"` (each provider's own raw status strings are mapped onto
    these three by the client module, not exposed further up)."""

    status: str
    subscription_code: Optional[str]
    current_period_end: Optional[datetime]


class PaymentProvider(Protocol):
    """Implemented by `PaystackProvider` (paystack_client.py) and
    `FlutterwaveProvider` (flutterwave_client.py)."""

    name: str  # "paystack" | "flutterwave"

    async def initialize_transaction(
        self, *, email: str, amount_kobo: int, callback_url: str, metadata: dict, plan_code: Optional[str] = None
    ) -> CheckoutResult:
        """Start a hosted-checkout transaction for a recurring paid plan.
        `amount_kobo` is the charge amount in the currency's smallest unit
        (kobo for NGN) — both Paystack and Flutterwave expect amounts this
        way. `plan_code` is whichever tier's Paystack Plan code / Flutterwave
        Payment Plan ID the caller resolved (see `payments.py`'s
        `_plan_code_for_tier`) — omitted entirely for a one-time charge with
        no recurring plan attached."""
        ...

    async def verify_transaction(self, reference: str) -> VerifyResult:
        """Look up a transaction's current status directly from the
        provider — used both by the manual `GET /verify/{reference}` route
        and, indirectly, to confirm what a webhook event claims happened."""
        ...

    async def cancel_subscription(self, *, subscription_code: str, subscription_token: Optional[str] = None) -> None:
        """Ask the provider to stop future recurring charges.
        `subscription_token` is Paystack-specific (its `/subscription/disable`
        call requires the subscription's `email_token` alongside its code,
        captured off the `subscription.create` webhook event) — Flutterwave
        ignores it. Kept as one uniform signature so the caller in
        `payments.py` never needs to branch on provider. Local state
        (`Subscription.cancel_at_period_end`) is updated by the caller —
        this only talks to the provider."""
        ...
