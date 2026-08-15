import datetime
from decimal import Decimal

from app.services.exchange_rates import get_historical_rate, upsert_exchange_rate


async def test_same_currency_returns_rate_one(db_session):
    rate = await get_historical_rate(db_session, "NGN", "NGN", datetime.date(2026, 1, 1))
    assert rate == 100


async def test_uses_historical_rate_at_order_date_not_the_latest_rate(db_session):
    """The core requirement of 1.12: order_date's rate, not 'today's'/latest
    rate. Also covers the no-exact-match case: 2026-01-15 has no row of its
    own, so it falls back to the most recent rate on or before that date
    (2026-01-01's), not the later 2026-06-01 one."""
    await upsert_exchange_rate(db_session, "USD", "NGN", datetime.date(2026, 1, 1), 150000)
    await upsert_exchange_rate(db_session, "USD", "NGN", datetime.date(2026, 6, 1), 170000)

    historical = await get_historical_rate(db_session, "USD", "NGN", datetime.date(2026, 1, 15))
    assert historical == 150000

    later = await get_historical_rate(db_session, "USD", "NGN", datetime.date(2026, 6, 15))
    assert later == 170000


async def test_returns_none_when_no_rate_known_for_or_before_that_date(db_session):
    await upsert_exchange_rate(db_session, "USD", "NGN", datetime.date(2026, 6, 1), 170000)

    rate = await get_historical_rate(db_session, "USD", "NGN", datetime.date(2026, 1, 1))
    assert rate is None


async def test_upsert_overwrites_rate_for_same_currency_pair_and_date(db_session):
    await upsert_exchange_rate(db_session, "USD", "NGN", datetime.date(2026, 1, 1), 150000)
    await upsert_exchange_rate(db_session, "USD", "NGN", datetime.date(2026, 1, 1), 155000)

    rate = await get_historical_rate(db_session, "USD", "NGN", datetime.date(2026, 1, 1))
    assert rate == 155000
