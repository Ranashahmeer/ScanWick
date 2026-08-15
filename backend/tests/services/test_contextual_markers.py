import datetime
import uuid
from decimal import Decimal

from sqlalchemy import select

from app.models.contextual_markers import ContextualMarker
from app.models.orders import Order, OrderDataSource, OrderStatus
from app.models.reconciliation_reports import AnalyzerType
from app.services.contextual_markers import (
    create_contextual_marker,
    get_marker_ranges,
    is_within_marker_ranges,
    reflag_orders_for_marker,
)


def _make_order(merchant_id, order_date, is_anomalous=False) -> Order:
    return Order(
        id=uuid.uuid4(),
        merchant_id=merchant_id,
        order_date=order_date,
        gross_revenue=100000,
        original_currency="NGN",
        status=OrderStatus.fulfilled,
        data_source=OrderDataSource.shopify_csv,
        is_anomalous=is_anomalous,
    )


def test_is_within_marker_ranges():
    ranges = [(datetime.date(2026, 1, 1), datetime.date(2026, 1, 31))]
    assert is_within_marker_ranges(datetime.date(2026, 1, 15), ranges) is True
    assert is_within_marker_ranges(datetime.date(2026, 1, 1), ranges) is True  # inclusive start
    assert is_within_marker_ranges(datetime.date(2026, 1, 31), ranges) is True  # inclusive end
    assert is_within_marker_ranges(datetime.date(2026, 2, 1), ranges) is False


async def test_get_marker_ranges_scoped_to_merchant_and_analyzer_type(db_session):
    merchant_id = uuid.uuid4()
    other_merchant_id = uuid.uuid4()

    await create_contextual_marker(
        db_session,
        merchant_id,
        AnalyzerType.ecommerce,
        "Promotion Period",
        datetime.date(2026, 1, 1),
        datetime.date(2026, 1, 31),
    )
    await create_contextual_marker(
        db_session,
        other_merchant_id,
        AnalyzerType.ecommerce,
        "Unrelated merchant's marker",
        datetime.date(2026, 1, 1),
        datetime.date(2026, 1, 31),
    )
    await create_contextual_marker(
        db_session,
        merchant_id,
        AnalyzerType.bank,
        "Wrong analyzer type",
        datetime.date(2026, 1, 1),
        datetime.date(2026, 1, 31),
    )

    ranges = await get_marker_ranges(db_session, merchant_id, AnalyzerType.ecommerce)
    assert ranges == [(datetime.date(2026, 1, 1), datetime.date(2026, 1, 31))]


async def test_creating_marker_retroactively_flags_existing_orders_inside_range(db_session):
    merchant_id = uuid.uuid4()

    inside_order = _make_order(merchant_id, datetime.datetime(2026, 1, 15, tzinfo=datetime.timezone.utc))
    boundary_order = _make_order(merchant_id, datetime.datetime(2026, 1, 31, tzinfo=datetime.timezone.utc))
    outside_order = _make_order(merchant_id, datetime.datetime(2026, 2, 1, tzinfo=datetime.timezone.utc))
    db_session.add_all([inside_order, boundary_order, outside_order])
    await db_session.commit()

    assert inside_order.is_anomalous is False
    assert boundary_order.is_anomalous is False
    assert outside_order.is_anomalous is False

    # Adding the marker now — after the orders already exist — must
    # retroactively flag the ones inside its range.
    await create_contextual_marker(
        db_session,
        merchant_id,
        AnalyzerType.ecommerce,
        "Inventory Shortage",
        datetime.date(2026, 1, 1),
        datetime.date(2026, 1, 31),
    )

    result = await db_session.execute(select(Order).where(Order.merchant_id == merchant_id))
    by_id = {o.id: o for o in result.scalars().all()}
    assert by_id[inside_order.id].is_anomalous is True
    assert by_id[boundary_order.id].is_anomalous is True  # inclusive end_date
    assert by_id[outside_order.id].is_anomalous is False


async def test_reflag_does_not_touch_orders_for_a_different_merchant(db_session):
    """Calls reflag_orders_for_marker directly (not via create_contextual_marker,
    which already triggers it) to check the returned count and scoping in
    isolation."""
    merchant_id = uuid.uuid4()
    other_merchant_id = uuid.uuid4()

    order = _make_order(merchant_id, datetime.datetime(2026, 1, 15, tzinfo=datetime.timezone.utc))
    other_order = _make_order(other_merchant_id, datetime.datetime(2026, 1, 15, tzinfo=datetime.timezone.utc))
    db_session.add_all([order, other_order])
    await db_session.commit()

    marker = ContextualMarker(
        id=uuid.uuid4(),
        merchant_id=merchant_id,
        analyzer_type=AnalyzerType.ecommerce,
        label="Promotion Period",
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 1, 31),
    )
    db_session.add(marker)
    await db_session.commit()

    count = await reflag_orders_for_marker(db_session, marker)

    assert count == 1
    await db_session.refresh(order)
    await db_session.refresh(other_order)
    assert order.is_anomalous is True
    assert other_order.is_anomalous is False
