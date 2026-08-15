import uuid
from datetime import datetime, timezone
from decimal import Decimal

from app.models.orders import Order, OrderDataSource, OrderStatus


async def test_get_dashboard_summary_found(client, db_session):
    merchant_id = uuid.uuid4()
    good = Order(
        id=uuid.uuid4(),
        merchant_id=merchant_id,
        order_date=datetime(2026, 1, 15, tzinfo=timezone.utc),
        gross_revenue=100000000,
        original_currency="NGN",
        status=OrderStatus.fulfilled,
        data_source=OrderDataSource.shopify_csv,
        is_anomalous=False,
    )
    anomalous = Order(
        id=uuid.uuid4(),
        merchant_id=merchant_id,
        order_date=datetime(2026, 1, 16, tzinfo=timezone.utc),
        gross_revenue=9999999900,
        original_currency="NGN",
        status=OrderStatus.fulfilled,
        data_source=OrderDataSource.shopify_csv,
        is_anomalous=True,
    )
    db_session.add_all([good, anomalous])
    await db_session.commit()

    response = await client.get(
        f"/api/v1/ecommerce/dashboard/summary?merchant_id={merchant_id}&date_from=2026-01-01&date_to=2026-01-31"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["total_orders"] == 1
    assert body["data"]["gross_revenue"]["value"] == 100000000.0
    assert body["meta"]["analysis_run_id"] is not None


async def test_get_dashboard_summary_invalid_merchant_id(client, db_session):
    response = await client.get("/api/v1/ecommerce/dashboard/summary?merchant_id=not-a-uuid")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_MERCHANT_ID"


async def test_get_dashboard_summary_invalid_date(client, db_session):
    response = await client.get(
        f"/api/v1/ecommerce/dashboard/summary?merchant_id={uuid.uuid4()}&date_from=not-a-date"
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_DATE"


async def test_get_dashboard_summary_requires_merchant_id(client, db_session):
    response = await client.get("/api/v1/ecommerce/dashboard/summary")
    assert response.status_code == 422


async def test_get_dashboard_summary_no_orders_at_all(client, db_session):
    response = await client.get(f"/api/v1/ecommerce/dashboard/summary?merchant_id={uuid.uuid4()}")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["total_orders"] == 0
    assert body["data"]["avg_order_value"] == 0.0


async def test_get_dashboard_revenue_gap_breakdown_sums_to_gross_minus_net(client, db_session):
    merchant_id = uuid.uuid4()
    order = Order(
        id=uuid.uuid4(),
        merchant_id=merchant_id,
        order_date=datetime(2026, 1, 15, tzinfo=timezone.utc),
        gross_revenue=425000000,
        original_currency="NGN",
        refund_amount=21000000,
        discount_amount=18000000,
        shipping_cost=24000000,
        processing_fees=9500000,
        allocated_ad_spend=34500000,
        status=OrderStatus.fulfilled,
        data_source=OrderDataSource.shopify_csv,
        is_anomalous=False,
    )
    db_session.add(order)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/ecommerce/dashboard/revenue?merchant_id={merchant_id}&date_from=2026-01-01&date_to=2026-01-31"
    )

    assert response.status_code == 200
    body = response.json()
    data = body["data"]
    gap_breakdown_sum = sum(data["gap_breakdown"].values())
    assert gap_breakdown_sum == data["gross_revenue"] - data["net_revenue"]
    assert gap_breakdown_sum == data["gap"]
    assert body["meta"]["analysis_run_id"] is not None


async def test_get_dashboard_revenue_invalid_merchant_id(client, db_session):
    response = await client.get("/api/v1/ecommerce/dashboard/revenue?merchant_id=not-a-uuid")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_MERCHANT_ID"
