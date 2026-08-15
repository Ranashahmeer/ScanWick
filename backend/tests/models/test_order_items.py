import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.models.order_items import OrderItem
from app.models.orders import Order, OrderDataSource, OrderStatus


async def _make_order(db_session) -> Order:
    order = Order(
        id=uuid.uuid4(),
        merchant_id=uuid.uuid4(),
        order_date=datetime(2026, 1, 15, tzinfo=timezone.utc),
        gross_revenue=230081,
        original_currency="NGN",
        status=OrderStatus.fulfilled,
        data_source=OrderDataSource.shopify_csv,
    )
    db_session.add(order)
    await db_session.commit()
    return order


def _make_item(order_id, merchant_id, **overrides) -> OrderItem:
    defaults = dict(
        id=uuid.uuid4(),
        order_id=order_id,
        merchant_id=merchant_id,
        sku="SKU-0042",
        quantity=2,
        unit_price=150000,
        unit_cogs=60000,
        unit_shipping_cost=7500,
        unit_return_cost=5000,
        unit_net_margin=77500,
    )
    defaults.update(overrides)
    return OrderItem(**defaults)


async def test_create_and_read_order_item(db_session):
    order = await _make_order(db_session)
    item = _make_item(order.id, order.merchant_id)
    db_session.add(item)
    await db_session.commit()

    result = await db_session.execute(select(OrderItem).where(OrderItem.id == item.id))
    fetched = result.scalar_one()

    assert fetched.sku == "SKU-0042"
    assert fetched.quantity == 2
    assert fetched.unit_price == 150000
    assert fetched.order_id == order.id


async def test_unit_cogs_can_be_null(db_session):
    order = await _make_order(db_session)
    item = _make_item(order.id, order.merchant_id, unit_cogs=None)
    db_session.add(item)
    await db_session.commit()

    result = await db_session.execute(select(OrderItem).where(OrderItem.id == item.id))
    assert result.scalar_one().unit_cogs is None


async def test_update_order_item(db_session):
    order = await _make_order(db_session)
    item = _make_item(order.id, order.merchant_id)
    db_session.add(item)
    await db_session.commit()

    item.unit_net_margin = -2000
    await db_session.commit()

    result = await db_session.execute(select(OrderItem).where(OrderItem.id == item.id))
    assert result.scalar_one().unit_net_margin == -2000


async def test_delete_order_item(db_session):
    order = await _make_order(db_session)
    item = _make_item(order.id, order.merchant_id)
    db_session.add(item)
    await db_session.commit()

    await db_session.delete(item)
    await db_session.commit()

    result = await db_session.execute(select(OrderItem).where(OrderItem.id == item.id))
    assert result.scalar_one_or_none() is None
