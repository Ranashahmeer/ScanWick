import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.merchant_settings import MerchantSettings


def _make_settings(**overrides) -> MerchantSettings:
    defaults = dict(
        id=uuid.uuid4(),
        merchant_id=uuid.uuid4(),
        base_currency="NGN",
        default_return_cost=50000,
    )
    defaults.update(overrides)
    return MerchantSettings(**defaults)


async def test_create_and_read_merchant_settings(db_session):
    settings = _make_settings()
    db_session.add(settings)
    await db_session.commit()

    result = await db_session.execute(select(MerchantSettings).where(MerchantSettings.id == settings.id))
    fetched = result.scalar_one()

    assert fetched.base_currency == "NGN"
    assert fetched.default_return_cost == 50000


async def test_update_merchant_settings(db_session):
    settings = _make_settings()
    db_session.add(settings)
    await db_session.commit()

    settings.default_return_cost = 75000
    await db_session.commit()

    result = await db_session.execute(select(MerchantSettings).where(MerchantSettings.id == settings.id))
    assert result.scalar_one().default_return_cost == 75000


async def test_delete_merchant_settings(db_session):
    settings = _make_settings()
    db_session.add(settings)
    await db_session.commit()

    await db_session.delete(settings)
    await db_session.commit()

    result = await db_session.execute(select(MerchantSettings).where(MerchantSettings.id == settings.id))
    assert result.scalar_one_or_none() is None


async def test_merchant_id_must_be_unique(db_session):
    merchant_id = uuid.uuid4()
    db_session.add(_make_settings(merchant_id=merchant_id))
    await db_session.commit()

    db_session.add(_make_settings(merchant_id=merchant_id))
    with pytest.raises(IntegrityError):
        await db_session.commit()
