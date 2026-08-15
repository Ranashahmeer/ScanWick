"""Thin client for Flutterwave's Payments/Subscriptions API v3 — the
fallback payment provider `app.services.payments.initiate_checkout`
automatically retries through when Paystack's API call fails. Same shape as
`paystack_client.py`/`mono_client.py`: a module-level base URL, one
`<Provider>APIError` exception, a private `_flw_*` HTTP helper, public
functions per endpoint.

Response shapes reflect Flutterwave's public v3 API docs as of this
assistant's training data — not verified against a live account; double-
check before going live, same caveat as `paystack_client.py`/`mono_client.py`.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

import httpx

from app.config import settings
from app.services.payment_provider import CheckoutResult, VerifyResult

FLW_BASE_URL = "https://api.flutterwave.com/v3"


class FlutterwaveAPIError(Exception):
    """Raised on any non-2xx response from the Flutterwave API, or when
    FLUTTERWAVE_SECRET_KEY isn't configured at all."""


def _parse_json_or_raise(response: httpx.Response) -> dict:
    """A 2xx status doesn't guarantee a JSON body (proxies/CDNs in front of
    an API can still return HTML on an edge case) — without this, a
    malformed response crashes the caller with a raw, uncaught
    JSONDecodeError instead of the clean FlutterwaveAPIError every other
    failure mode already produces."""
    try:
        return response.json()
    except ValueError as exc:
        raise FlutterwaveAPIError(f"Flutterwave API returned a non-JSON response: {response.text[:500]}") from exc


async def _flw_post(path: str, *, json: dict) -> dict:
    if not settings.flutterwave_secret_key:
        raise FlutterwaveAPIError("Flutterwave is not configured (FLUTTERWAVE_SECRET_KEY is empty).")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{FLW_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {settings.flutterwave_secret_key}"},
            json=json,
        )
    if response.status_code >= 400:
        raise FlutterwaveAPIError(f"Flutterwave API error {response.status_code}: {response.text}")
    return _parse_json_or_raise(response)


async def _flw_put(path: str, *, json: dict) -> dict:
    if not settings.flutterwave_secret_key:
        raise FlutterwaveAPIError("Flutterwave is not configured (FLUTTERWAVE_SECRET_KEY is empty).")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.put(
            f"{FLW_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {settings.flutterwave_secret_key}"},
            json=json,
        )
    if response.status_code >= 400:
        raise FlutterwaveAPIError(f"Flutterwave API error {response.status_code}: {response.text}")
    return _parse_json_or_raise(response)


async def _flw_get(path: str) -> dict:
    if not settings.flutterwave_secret_key:
        raise FlutterwaveAPIError("Flutterwave is not configured (FLUTTERWAVE_SECRET_KEY is empty).")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{FLW_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {settings.flutterwave_secret_key}"},
        )
    if response.status_code >= 400:
        raise FlutterwaveAPIError(f"Flutterwave API error {response.status_code}: {response.text}")
    return _parse_json_or_raise(response)


async def initialize_payment(
    *, email: str, amount_kobo: int, callback_url: str, metadata: dict, payment_plan_id: Optional[str] = None
) -> dict:
    # Flutterwave's `tx_ref` is our own client-generated reference (unlike
    # Paystack, which mints its `reference` server-side) -- generated here
    # so PaystackProvider/FlutterwaveProvider both hand back a `reference`
    # the caller can treat identically regardless of who assigned it.
    tx_ref = f"scanwick-{uuid.uuid4().hex}"
    payload = {
        "tx_ref": tx_ref,
        # Flutterwave takes major currency units, not minor (kobo). Through
        # Decimal rather than plain `amount_kobo / 100` float division —
        # `amount_kobo` is always a whole integer, so this is exact; float
        # division of an integer by 100 happens to round-trip cleanly for
        # every 2-decimal-place NGN amount in practice, but going through
        # Decimal first makes that "exact by construction" instead of
        # "exact because of how IEEE754 happens to behave here."
        "amount": float(Decimal(amount_kobo) / 100),
        "currency": "NGN",
        "redirect_url": callback_url,
        "customer": {"email": email},
        "meta": metadata,
    }
    if payment_plan_id:
        payload["payment_plan"] = payment_plan_id
    response = await _flw_post("/payments", json=payload)
    data = response.get("data") or {}
    return {"authorization_url": data.get("link"), "reference": tx_ref}


async def verify_transaction(reference: str) -> dict:
    response = await _flw_get(f"/transactions/verify_by_reference?tx_ref={reference}")
    return response.get("data") or {}


async def cancel_subscription(subscription_id: str) -> None:
    # Flutterwave's real cancel-subscription endpoint is PUT, not POST —
    # confirmed by hitting it live with the wrong method during testing,
    # which crashed instead of erroring cleanly (see _parse_json_or_raise).
    await _flw_put(f"/subscriptions/{subscription_id}/cancel", json={})


def _map_verify_status(flw_status: Optional[str]) -> str:
    """Flutterwave's verify `status` is "successful" on success, or
    "failed"/"cancelled" otherwise -- normalized to the same three-value
    success/pending/failed vocabulary `PaystackProvider` maps onto."""
    if flw_status == "successful":
        return "success"
    if flw_status in ("failed", "cancelled"):
        return "failed"
    return "pending"


class FlutterwaveProvider:
    """Implements `app.services.payment_provider.PaymentProvider`."""

    name = "flutterwave"

    async def initialize_transaction(
        self, *, email: str, amount_kobo: int, callback_url: str, metadata: dict, plan_code: Optional[str] = None
    ) -> CheckoutResult:
        data = await initialize_payment(
            email=email,
            amount_kobo=amount_kobo,
            callback_url=callback_url,
            metadata=metadata,
            payment_plan_id=plan_code,
        )
        return CheckoutResult(authorization_url=data["authorization_url"], reference=data["reference"])

    async def verify_transaction(self, reference: str) -> VerifyResult:
        data = await verify_transaction(reference)
        return VerifyResult(
            status=_map_verify_status(data.get("status")),
            subscription_code=str(data.get("id")) if data.get("id") is not None else None,
            current_period_end=None,
        )

    async def cancel_subscription(self, *, subscription_code: str, subscription_token: Optional[str] = None) -> None:
        # subscription_token is Paystack-specific; Flutterwave's cancel only
        # needs the subscription id, already carried in subscription_code.
        await cancel_subscription(subscription_code)
