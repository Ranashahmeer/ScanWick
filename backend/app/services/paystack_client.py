"""Thin client for Paystack's Transactions/Subscriptions API — the primary
payment provider (see `app.services.payments` for the fallback-to-Flutterwave
logic). Modeled directly on `mono_client.py`'s shape: a module-level base
URL, one `<Provider>APIError` exception, a private `_paystack_*` HTTP
helper, and public functions per endpoint.

Response shapes reflect Paystack's public API docs as of this assistant's
training data — like `mono_client.py`, this hasn't been verified against a
live account, so double-check field names (especially `verify_transaction`'s
subscription fields, which Paystack's docs are not fully explicit about)
against Paystack's current docs before going live.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.config import settings
from app.services.payment_provider import CheckoutResult, VerifyResult

PAYSTACK_BASE_URL = "https://api.paystack.co"

logger = logging.getLogger("app.paystack")


class PaystackAPIError(Exception):
    """Raised on any non-2xx response from the Paystack API, or when
    PAYSTACK_SECRET_KEY isn't configured at all."""


def _parse_json_or_raise(response: httpx.Response) -> dict:
    """A 2xx status doesn't guarantee a JSON body (proxies/CDNs in front of
    an API can still return HTML on an edge case) — without this, a
    malformed response crashes the caller with a raw, uncaught
    JSONDecodeError instead of the clean PaystackAPIError every other
    failure mode already produces. (Confirmed as a real failure mode on the
    Flutterwave client this was copied from — fixed here defensively too.)"""
    try:
        return response.json()
    except ValueError as exc:
        raise PaystackAPIError(f"Paystack API returned a non-JSON response: {response.text[:500]}") from exc


async def _paystack_post(path: str, *, json: dict) -> dict:
    if not settings.paystack_secret_key:
        raise PaystackAPIError("Paystack is not configured (PAYSTACK_SECRET_KEY is empty).")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{PAYSTACK_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {settings.paystack_secret_key}"},
            json=json,
        )
    if response.status_code >= 400:
        raise PaystackAPIError(f"Paystack API error {response.status_code}: {response.text}")
    return _parse_json_or_raise(response)


async def _paystack_get(path: str) -> dict:
    if not settings.paystack_secret_key:
        raise PaystackAPIError("Paystack is not configured (PAYSTACK_SECRET_KEY is empty).")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{PAYSTACK_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {settings.paystack_secret_key}"},
        )
    if response.status_code >= 400:
        raise PaystackAPIError(f"Paystack API error {response.status_code}: {response.text}")
    return _parse_json_or_raise(response)


async def initialize_transaction(
    *, email: str, amount_kobo: int, callback_url: str, metadata: dict, plan_code: Optional[str] = None
) -> dict:
    payload = {
        "email": email,
        "amount": amount_kobo,
        "callback_url": callback_url,
        "metadata": metadata,
    }
    if plan_code:
        payload["plan"] = plan_code
    response = await _paystack_post("/transaction/initialize", json=payload)
    return response.get("data") or {}


async def verify_transaction(reference: str) -> dict:
    response = await _paystack_get(f"/transaction/verify/{reference}")
    return response.get("data") or {}


async def disable_subscription(*, subscription_code: str, email_token: str) -> None:
    await _paystack_post("/subscription/disable", json={"code": subscription_code, "token": email_token})


def _map_verify_status(paystack_status: Optional[str]) -> str:
    """Paystack's transaction-verify `status` is already one of
    success/failed/abandoned — collapse "abandoned" (user never completed
    checkout) into "failed" since callers only distinguish success/pending/
    failed, not why a non-success happened."""
    if paystack_status == "success":
        return "success"
    if paystack_status in ("failed", "abandoned"):
        return "failed"
    return "pending"


class PaystackProvider:
    """Implements `app.services.payment_provider.PaymentProvider`."""

    name = "paystack"

    async def initialize_transaction(
        self, *, email: str, amount_kobo: int, callback_url: str, metadata: dict, plan_code: Optional[str] = None
    ) -> CheckoutResult:
        data = await initialize_transaction(
            email=email, amount_kobo=amount_kobo, callback_url=callback_url, metadata=metadata, plan_code=plan_code
        )
        return CheckoutResult(authorization_url=data["authorization_url"], reference=data["reference"])

    async def verify_transaction(self, reference: str) -> VerifyResult:
        data = await verify_transaction(reference)
        subscription = data.get("subscription") or {}
        return VerifyResult(
            status=_map_verify_status(data.get("status")),
            subscription_code=subscription.get("subscription_code"),
            current_period_end=None,
        )

    async def cancel_subscription(self, *, subscription_code: str, subscription_token: Optional[str] = None) -> None:
        if not subscription_token:
            raise PaystackAPIError("Cannot disable a Paystack subscription without its email_token.")
        await disable_subscription(subscription_code=subscription_code, email_token=subscription_token)
