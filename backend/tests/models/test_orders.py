import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.models.orders import Order, OrderDataSource, OrderStatus


def _make_order(**overrides) -> Order:
    defaults = dict(
        id=uuid.uuid4(),
        merchant_id=uuid.uuid4(),
        external_order_id="SHOPIFY-1001",
        order_date=datetime(2026, 1, 15, tzinfo=timezone.utc),
        gross_revenue=230081,
        original_currency="NGN",
        base_currency_amount=230081,
        exchange_rate_at_order=100,
        refund_amount=0,
        discount_amount=0,
        shipping_cost=15000,
        processing_fees=3000,
        allocated_ad_spend=8000,
        cogs=90000,
        net_margin=114081,
        channel="organic",
        customer_id=uuid.uuid4(),
        status=OrderStatus.fulfilled,
        data_source=OrderDataSource.shopify_csv,
    )
    defaults.update(overrides)
    return Order(**defaults)


async def test_create_and_read_order(db_session):
    order = _make_order()
    db_session.add(order)
    await db_session.commit()

    result = await db_session.execute(select(Order).where(Order.id == order.id))
    fetched = result.scalar_one()

    assert fetched.external_order_id == "SHOPIFY-1001"
    assert fetched.gross_revenue == 230081
    assert fetched.original_currency == "NGN"
    assert fetched.status == OrderStatus.fulfilled
    assert fetched.data_source == OrderDataSource.shopify_csv
    assert fetched.is_anomalous is False


async def test_is_anomalous_defaults_false(db_session):
    order = _make_order()
    db_session.add(order)
    await db_session.commit()

    result = await db_session.execute(select(Order).where(Order.id == order.id))
    assert result.scalar_one().is_anomalous is False


async def test_is_anomalous_can_be_set_true(db_session):
    order = _make_order(is_anomalous=True)
    db_session.add(order)
    await db_session.commit()

    result = await db_session.execute(select(Order).where(Order.id == order.id))
    assert result.scalar_one().is_anomalous is True


async def test_update_order(db_session):
    order = _make_order()
    db_session.add(order)
    await db_session.commit()

    order.net_margin = -5000
    await db_session.commit()

    result = await db_session.execute(select(Order).where(Order.id == order.id))
    assert result.scalar_one().net_margin == -5000


async def test_delete_order(db_session):
    order = _make_order()
    db_session.add(order)
    await db_session.commit()

    await db_session.delete(order)
    await db_session.commit()

    result = await db_session.execute(select(Order).where(Order.id == order.id))
    assert result.scalar_one_or_none() is None


async def test_each_data_source_enum_value_is_storable(db_session):
    for source in OrderDataSource:
        order = _make_order(id=uuid.uuid4(), data_source=source)
        db_session.add(order)
    await db_session.commit()

    result = await db_session.execute(select(Order.data_source))
    stored_sources = {row[0] for row in result.all()}
    assert stored_sources == set(OrderDataSource)
