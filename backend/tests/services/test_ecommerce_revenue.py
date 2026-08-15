import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from app.models.merchant_settings import MerchantSettings
from app.models.orders import Order, OrderDataSource, OrderStatus
from app.services.ecommerce_revenue import compute_dashboard_revenue


def _make_order(merchant_id, order_date, gross_revenue, is_anomalous=False, **overrides) -> Order:
    defaults = dict(
        id=uuid.uuid4(),
        merchant_id=merchant_id,
        order_date=order_date,
        gross_revenue=int(float(gross_revenue) * 100),
        original_currency="NGN",
        refund_amount=0,
        discount_amount=0,
        shipping_cost=0,
        processing_fees=0,
        allocated_ad_spend=0,
        status=OrderStatus.fulfilled,
        data_source=OrderDataSource.shopify_csv,
        is_anomalous=is_anomalous,
    )
    defaults.update(overrides)
    return Order(**defaults)


async def test_gap_breakdown_sums_correctly_against_gross_minus_net(db_session):
    """The task's explicit ask."""
    merchant_id = uuid.uuid4()
    db_session.add(
        _make_order(
            merchant_id,
            datetime(2026, 1, 15, tzinfo=timezone.utc),
            "4250000.00",
            refund_amount=21000000,
            discount_amount=18000000,
            shipping_cost=24000000,
            processing_fees=9500000,
            allocated_ad_spend=34500000,
        )
    )
    await db_session.commit()

    data, analysis_run_id, missing_fields = await compute_dashboard_revenue(
        db_session, merchant_id, date(2026, 1, 1), date(2026, 1, 31)
    )

    gap_breakdown_sum = sum(data["gap_breakdown"].values())
    assert missing_fields == []
    assert gap_breakdown_sum == data["gross_revenue"] - data["net_revenue"]
    assert gap_breakdown_sum == data["gap"]
    assert data["gap"] == 107000000
    assert analysis_run_id is not None


async def test_gap_breakdown_has_exactly_the_five_spec_components(db_session):
    merchant_id = uuid.uuid4()
    db_session.add(_make_order(merchant_id, datetime(2026, 1, 15, tzinfo=timezone.utc), "100000.00"))
    await db_session.commit()

    data, _, missing_fields = await compute_dashboard_revenue(db_session, merchant_id, date(2026, 1, 1), date(2026, 1, 31))

    assert set(data["gap_breakdown"].keys()) == {"returns", "discounts", "shipping", "processing", "ad_spend"}
    assert missing_fields == []


async def test_dashboard_revenue_excludes_anomalous_orders(db_session):
    merchant_id = uuid.uuid4()
    db_session.add(_make_order(merchant_id, datetime(2026, 1, 15, tzinfo=timezone.utc), "500000.00"))
    db_session.add(
        _make_order(merchant_id, datetime(2026, 1, 16, tzinfo=timezone.utc), "999999999.00", is_anomalous=True)
    )
    await db_session.commit()

    data, _, missing_fields = await compute_dashboard_revenue(db_session, merchant_id, date(2026, 1, 1), date(2026, 1, 31))

    assert data["gross_revenue"] == 50000000
    assert data["currency"] == "NGN"
    assert missing_fields == []


async def test_monthly_trend_groups_by_calendar_month(db_session):
    merchant_id = uuid.uuid4()
    db_session.add(_make_order(merchant_id, datetime(2026, 1, 5, tzinfo=timezone.utc), "1000000.00"))
    db_session.add(_make_order(merchant_id, datetime(2026, 1, 20, tzinfo=timezone.utc), "400000.00"))
    db_session.add(_make_order(merchant_id, datetime(2026, 2, 10, tzinfo=timezone.utc), "700000.00"))
    await db_session.commit()

    data, _, missing_fields = await compute_dashboard_revenue(db_session, merchant_id, date(2026, 1, 1), date(2026, 2, 28))

    assert data["monthly_trend"] == [
        {"month": "2026-01", "gross": 140000000, "net": 140000000},
        {"month": "2026-02", "gross": 70000000, "net": 70000000},
    ]


async def test_dashboard_revenue_handles_zero_orders(db_session):
    merchant_id = uuid.uuid4()
    data, analysis_run_id, missing_fields = await compute_dashboard_revenue(
        db_session, merchant_id, date(2026, 1, 1), date(2026, 1, 31)
    )

    assert data["gross_revenue"] == 0
    assert data["net_revenue"] == 0
    assert data["gap"] == 0
    assert data["monthly_trend"] == []
    assert missing_fields == []
    assert analysis_run_id is not None


async def test_dashboard_revenue_uses_merchant_base_currency(db_session):
    merchant_id = uuid.uuid4()
    db_session.add(MerchantSettings(id=uuid.uuid4(), merchant_id=merchant_id, base_currency="USD"))
    db_session.add(
        _make_order(
            merchant_id,
            datetime(2026, 1, 15, tzinfo=timezone.utc),
            "1000.00",
            original_currency="USD",
            base_currency_amount=100000,
            exchange_rate_at_order=100,
        )
    )
    await db_session.commit()

    data, _, missing_fields = await compute_dashboard_revenue(
        db_session, merchant_id, date(2026, 1, 1), date(2026, 1, 31)
    )

    assert data["gross_revenue"] == 100000
    assert data["currency"] == "USD"
    assert data["included_orders"] == 1
    assert data["excluded_orders_due_to_missing_conversion"] == 0
    assert missing_fields == []


async def test_dashboard_revenue_excludes_foreign_orders_missing_conversion(db_session):
    merchant_id = uuid.uuid4()
    db_session.add(
        _make_order(
            merchant_id,
            datetime(2026, 1, 15, tzinfo=timezone.utc),
            "1000.00",
            original_currency="USD",
            base_currency_amount=None,
            exchange_rate_at_order=None,
        )
    )
    await db_session.commit()

    data, _, missing_fields = await compute_dashboard_revenue(
        db_session, merchant_id, date(2026, 1, 1), date(2026, 1, 31)
    )

    assert data["gross_revenue"] == 0
    assert data["net_revenue"] == 0
    assert data["currency"] == "NGN"
    assert data["included_orders"] == 0
    assert data["excluded_orders_due_to_missing_conversion"] == 1
    assert missing_fields == ["base_currency_amount"]
