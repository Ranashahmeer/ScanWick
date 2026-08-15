from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.services import fx_rates
from app.services.exchange_rates import get_historical_rate

# Captured at import time (before the autouse _no_real_fx_rate_calls fixture
# in conftest.py monkeypatches fx_rates.fetch_live_usd_ngn_rate for every
# test) — the one test below that needs the REAL parsing/error-handling
# logic, not the fixed test double, calls this reference instead of the
# module attribute.
_REAL_FETCH_LIVE_RATE = fx_rates.fetch_live_usd_ngn_rate


async def test_get_current_rate_uses_cached_rate_without_a_network_call(db_session):
    await fx_rates.upsert_exchange_rate(db_session, "USD", "NGN", fx_rates._today_utc(), 160000)

    with patch.object(fx_rates, "fetch_live_usd_ngn_rate", new=AsyncMock()) as mock_fetch:
        rate = await fx_rates.get_current_usd_ngn_rate(db_session)

    mock_fetch.assert_not_awaited()
    assert rate == 160000


async def test_get_current_rate_fetches_live_and_caches_when_nothing_synced_today(db_session):
    with patch.object(fx_rates, "fetch_live_usd_ngn_rate", new=AsyncMock(return_value=155000)):
        rate = await fx_rates.get_current_usd_ngn_rate(db_session)

    assert rate == 155000
    cached = await get_historical_rate(db_session, "USD", "NGN", fx_rates._today_utc())
    assert cached == 155000


async def test_get_current_rate_falls_back_to_configured_rate_on_total_outage(db_session, monkeypatch):
    monkeypatch.setattr("app.config.settings.fallback_usd_ngn_rate", 1234.0)

    with patch.object(
        fx_rates, "fetch_live_usd_ngn_rate", new=AsyncMock(side_effect=fx_rates.FxRateFetchError("down"))
    ):
        rate = await fx_rates.get_current_usd_ngn_rate(db_session)

    assert rate == 123400


async def test_sync_upserts_today_in_place_not_a_new_row_each_time(db_session):
    with patch.object(fx_rates, "fetch_live_usd_ngn_rate", new=AsyncMock(return_value=150000)):
        await fx_rates.sync_usd_ngn_rate(db_session)
    with patch.object(fx_rates, "fetch_live_usd_ngn_rate", new=AsyncMock(return_value=151000)):
        await fx_rates.sync_usd_ngn_rate(db_session)

    rate = await get_historical_rate(db_session, "USD", "NGN", fx_rates._today_utc())
    assert rate == 151000


async def test_fetch_live_rate_raises_on_missing_ngn_rate():
    """Exercises the real fetch_live_usd_ngn_rate parsing logic (bypassing
    the autouse test-isolation mock via the reference captured at import
    time above) — a response missing an NGN rate must raise, not silently
    return None or KeyError."""
    import httpx

    class _FakeResponse:
        status_code = 200

        def json(self):
            return {"result": "success", "rates": {"USD": 1, "EUR": 0.9}}  # no NGN

    async def _fake_get(self, url):
        return _FakeResponse()

    with patch.object(httpx.AsyncClient, "get", new=_fake_get):
        try:
            await _REAL_FETCH_LIVE_RATE()
            assert False, "expected FxRateFetchError"
        except fx_rates.FxRateFetchError:
            pass


async def test_fetch_live_rate_raises_on_non_success_result():
    """Same real-implementation test as above, for the other failure mode:
    the API responding 200 but with result != "success" (e.g. a malformed
    base currency)."""
    import httpx

    class _FakeResponse:
        status_code = 200

        def json(self):
            return {"result": "error", "error-type": "unsupported-code"}

    async def _fake_get(self, url):
        return _FakeResponse()

    with patch.object(httpx.AsyncClient, "get", new=_fake_get):
        try:
            await _REAL_FETCH_LIVE_RATE()
            assert False, "expected FxRateFetchError"
        except fx_rates.FxRateFetchError:
            pass
