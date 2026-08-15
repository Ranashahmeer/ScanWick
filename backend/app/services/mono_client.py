"""Thin client for Mono's open banking API (Nigeria/Ghana/Kenya).

Shape assumed here (account details: id/accountNumber/currency/institution;
transactions: paginated, amount/balance in the currency's minor unit —
kobo/pesewas/cents; type: "credit"/"debit") reflects Mono's v2 API as of this
assistant's training data. Mono's actual current docs should be checked
before going live — this wasn't verified against a real account, since
1.23's own task explicitly calls for mocking the API, not hitting it live.
"""
from typing import Optional

import httpx

from app.config import settings

MONO_BASE_URL = "https://api.withmono.com/v2"


class MonoAPIError(Exception):
    """Raised on any non-2xx response from the Mono API."""


async def _mono_get(path: str, *, params: Optional[dict] = None) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{MONO_BASE_URL}{path}",
            headers={"mono-sec-key": settings.mono_secret_key},
            params=params,
        )
    if response.status_code >= 400:
        raise MonoAPIError(f"Mono API error {response.status_code}: {response.text}")
    return response.json()


async def fetch_account_details(mono_account_id: str) -> dict:
    """Real account metadata (account number, currency, institution/bank
    name) directly from Mono — more reliable than the CSV/PDF paths having
    to heuristically detect this from tabular transaction data."""
    payload = await _mono_get(f"/accounts/{mono_account_id}")
    return (payload.get("data") or {}).get("account") or {}


async def fetch_account_transactions_page(mono_account_id: str, *, page: int = 1) -> dict:
    return await _mono_get(f"/accounts/{mono_account_id}/transactions", params={"page": page})


async def fetch_all_account_transactions(mono_account_id: str) -> list[dict]:
    """Walks every page of an account's transaction history."""
    all_transactions: list[dict] = []
    page = 1
    while True:
        payload = await fetch_account_transactions_page(mono_account_id, page=page)
        data = payload.get("data") or []
        all_transactions.extend(data)
        paging = payload.get("paging") or {}
        total_pages = paging.get("totalPages", page)
        if not data or page >= total_pages:
            break
        page += 1
    return all_transactions
