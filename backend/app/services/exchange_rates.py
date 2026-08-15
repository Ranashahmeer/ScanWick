import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exchange_rates import ExchangeRate


async def get_historical_rate(
    db: AsyncSession, quote_currency: str, base_currency: str, as_of: date
) -> Optional[Decimal]:
    """Returns the exchange rate for converting `quote_currency` into
    `base_currency` as of `as_of` — the latest known rate on or before that
    date, never a rate from after it (this is what makes it "the order_date
    rate," not "today's rate"). Returns None if no rate is known for that
    date or earlier — callers should leave the conversion fields null rather
    than fabricate a rate.
    """
    if quote_currency == base_currency:
        return 1.000000

    result = await db.execute(
        select(ExchangeRate)
        .where(
            ExchangeRate.quote_currency == quote_currency,
            ExchangeRate.base_currency == base_currency,
            ExchangeRate.rate_date <= as_of,
        )
        .order_by(ExchangeRate.rate_date.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return row.rate if row else None


async def upsert_exchange_rate(
    db: AsyncSession, quote_currency: str, base_currency: str, rate_date: date, rate: Decimal
) -> ExchangeRate:
    """Seeds/updates a single historical rate. Stand-in for a real FX
    provider sync job, which doesn't exist yet — no specific provider is
    named anywhere in the spec."""
    result = await db.execute(
        select(ExchangeRate).where(
            ExchangeRate.quote_currency == quote_currency,
            ExchangeRate.base_currency == base_currency,
            ExchangeRate.rate_date == rate_date,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.rate = rate
        await db.commit()
        return existing

    row = ExchangeRate(
        id=uuid.uuid4(), quote_currency=quote_currency, base_currency=base_currency, rate_date=rate_date, rate=rate
    )
    db.add(row)
    await db.commit()
    return row
