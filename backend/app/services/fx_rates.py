"""Live USD -> NGN exchange rate sync. Subscription checkout (see
app.services.payments) prices each paid tier in a fixed USD amount and
converts it to NGN kobo at checkout time using the rate this module
maintains — Paystack/Flutterwave settle in NGN in this app, not USD, so the
NGN amount actually charged is re-derived from the live rate rather than a
stale hardcoded figure.

Reuses the existing `exchange_rates` table/service (app.services.exchange_rates,
already built for ingestion's "convert at order_date rate" requirement) as
the cache: syncing "today's" USD->NGN rate more than once just upserts the
same row in place, it never accumulates duplicate rows per sync.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery_app
from app.config import settings
from app.database import async_session
from app.services.exchange_rates import get_historical_rate, upsert_exchange_rate

logger = logging.getLogger("app.fx_rates")

# Free, keyless, CORS-open public endpoint (exchangerate-api.com's "open"
# tier) — verified against the live API while building this. No account or
# API key needed, matching this project's existing preference for
# zero-setup integrations (see mono_secret_key's "free startup tier" note).
FX_API_URL = "https://open.er-api.com/v6/latest/USD"


class FxRateFetchError(Exception):
    """Raised when the live FX rate can't be fetched, or the response has
    no NGN rate in it."""


def _today_utc():
    """UTC, not the server's local `date.today()` — Celery is already
    configured for UTC (celery_app.py), and pinning this the same way keeps
    "today's rate" consistent between the API process and a Celery worker
    even if they happen to run in different timezones/regions, and avoids
    a spurious extra sync right at a local-midnight boundary that isn't
    also the UTC one."""
    return datetime.now(timezone.utc).date()


async def fetch_live_usd_ngn_rate() -> Decimal:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(FX_API_URL)
    if response.status_code >= 400:
        raise FxRateFetchError(f"FX rate API error {response.status_code}: {response.text}")

    payload = response.json()
    if payload.get("result") != "success":
        raise FxRateFetchError(f"FX rate API returned a non-success result: {payload}")

    rate = (payload.get("rates") or {}).get("NGN")
    if rate is None:
        raise FxRateFetchError("FX rate API response has no NGN rate.")
    return Decimal(str(rate))


async def sync_usd_ngn_rate(db: AsyncSession) -> Decimal:
    """Fetches the live rate and stores it as today's rate. Called hourly
    by the Celery beat schedule (see celery_app.py), and on-demand by
    get_current_usd_ngn_rate() below if nothing's been synced yet today."""
    rate = await fetch_live_usd_ngn_rate()
    await upsert_exchange_rate(db, "USD", "NGN", _today_utc(), rate)
    logger.info("Synced USD->NGN rate: %s", rate)
    return rate


async def get_current_usd_ngn_rate(db: AsyncSession) -> Decimal:
    """What app.services.payments actually calls at checkout time.

    Prefers today's already-synced rate (fast, no network call — the
    common case, kept fresh by the hourly beat task). Falls back to
    fetching live on demand if nothing's been synced yet today (e.g. right
    after a fresh deploy, before the first hourly tick has run) — this is
    also what makes "the rate used is always current" true even in that
    gap. Falls back to a hardcoded emergency rate only if that live fetch
    itself fails too (a real FX-provider outage), so checkout never hard-
    fails over this — it just risks a possibly-stale rate for as long as
    the outage lasts."""
    cached = await get_historical_rate(db, "USD", "NGN", _today_utc())
    if cached is not None:
        return cached

    try:
        return await sync_usd_ngn_rate(db)
    except FxRateFetchError:
        logger.warning("Live USD->NGN fetch failed and no cached rate exists today — using fallback_usd_ngn_rate.")
        return Decimal(str(settings.fallback_usd_ngn_rate))


# ── Celery task (hourly — see celery_app.py's beat_schedule) ────────────────

@celery_app.task(name="fx.sync_usd_ngn_rate")
def sync_usd_ngn_rate_task() -> dict:
    return asyncio.run(_sync_usd_ngn_rate_async())


async def _sync_usd_ngn_rate_async() -> dict:
    async with async_session() as db:
        try:
            rate = await sync_usd_ngn_rate(db)
        except FxRateFetchError as exc:
            logger.warning("Hourly USD->NGN sync failed: %s", exc)
            return {"synced": False, "error": str(exc)}
    return {"synced": True, "rate": str(rate)}
