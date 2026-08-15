import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.models.orders import Order, OrderDataSource, OrderStatus
from app.models.reconciliation_reports import AnalyzerType, ReconciliationReport
from app.models.uploads import Upload
from app.services.ecommerce_dashboard import compute_dashboard_summary


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


async def test_dashboard_summary_excludes_anomalous_orders_from_every_aggregate(db_session):
    """The task's explicit ask."""
    merchant_id = uuid.uuid4()
    good = _make_order(merchant_id, datetime(2026, 1, 15, tzinfo=timezone.utc), "1000000.00")
    anomalous = _make_order(
        merchant_id, datetime(2026, 1, 16, tzinfo=timezone.utc), "999999999.00", is_anomalous=True
    )
    db_session.add_all([good, anomalous])
    await db_session.commit()

    data, analysis_run_id, _ = await compute_dashboard_summary(
        db_session, merchant_id, date(2026, 1, 1), date(2026, 1, 31)
    )

    assert data["total_orders"] == 1
    assert data["gross_revenue"]["value"] == 100000000
    assert analysis_run_id is not None


async def test_dashboard_summary_full_response_shape(db_session):
    merchant_id = uuid.uuid4()
    db_session.add(_make_order(merchant_id, datetime(2026, 1, 15, tzinfo=timezone.utc), "500000.00"))
    await db_session.commit()

    data, _, _ = await compute_dashboard_summary(db_session, merchant_id, date(2026, 1, 1), date(2026, 1, 31))

    assert set(data.keys()) == {
        "period",
        "gross_revenue",
        "net_revenue",
        "total_orders",
        "avg_order_value",
        "data_freshness",
    }
    assert data["period"] == {"start": "2026-01-01", "end": "2026-01-31"}
    assert set(data["gross_revenue"].keys()) == {"value", "currency", "change_pct"}


async def test_net_revenue_subtracts_returns_discounts_shipping_processing_ad_spend_but_not_cogs(db_session):
    merchant_id = uuid.uuid4()
    order = _make_order(
        merchant_id,
        datetime(2026, 1, 15, tzinfo=timezone.utc),
        "4250000.00",
        refund_amount=21000000,
        discount_amount=18000000,
        shipping_cost=24000000,
        processing_fees=9500000,
        allocated_ad_spend=34500000,
        cogs=999999900,  # deliberately huge — must NOT affect net_revenue (only net_margin subtracts cogs)
    )
    db_session.add(order)
    await db_session.commit()

    data, _, _ = await compute_dashboard_summary(db_session, merchant_id, date(2026, 1, 1), date(2026, 1, 31))

    assert data["net_revenue"]["value"] == 318000000  # 4,250,000 - 1,070,000 gap


async def test_change_pct_computed_against_prior_equal_length_period(db_session):
    merchant_id = uuid.uuid4()
    # Prior period (Dec 2025): 1,000,000. Current period (Jan 2026): 1,200,000 -> +20%.
    db_session.add(_make_order(merchant_id, datetime(2025, 12, 15, tzinfo=timezone.utc), "1000000.00"))
    db_session.add(_make_order(merchant_id, datetime(2026, 1, 15, tzinfo=timezone.utc), "1200000.00"))
    await db_session.commit()

    data, _, _ = await compute_dashboard_summary(db_session, merchant_id, date(2026, 1, 1), date(2026, 1, 31))

    assert data["gross_revenue"]["change_pct"] == 20.0


async def test_change_pct_is_none_when_no_prior_period_data(db_session):
    merchant_id = uuid.uuid4()
    db_session.add(_make_order(merchant_id, datetime(2026, 1, 15, tzinfo=timezone.utc), "1000000.00"))
    await db_session.commit()

    data, _, _ = await compute_dashboard_summary(db_session, merchant_id, date(2026, 1, 1), date(2026, 1, 31))

    assert data["gross_revenue"]["change_pct"] is None


async def test_avg_order_value_and_zero_orders_does_not_divide_by_zero(db_session):
    merchant_id = uuid.uuid4()
    data, _, _ = await compute_dashboard_summary(db_session, merchant_id, date(2026, 1, 1), date(2026, 1, 31))

    assert data["total_orders"] == 0
    assert data["avg_order_value"] == 0.0


async def test_writes_a_reconciliation_report_row(db_session):
    merchant_id = uuid.uuid4()
    db_session.add(_make_order(merchant_id, datetime(2026, 1, 15, tzinfo=timezone.utc), "1000000.00"))
    await db_session.commit()

    _, analysis_run_id, _ = await compute_dashboard_summary(db_session, merchant_id, date(2026, 1, 1), date(2026, 1, 31))

    report = (
        await db_session.execute(select(ReconciliationReport).where(ReconciliationReport.id == uuid.UUID(analysis_run_id)))
    ).scalar_one()
    assert report.merchant_id == merchant_id
    assert report.records_analyzed == 1


async def test_data_freshness_reflects_order_recency_not_upload_recency(db_session):
    """Audit #31: `is_stale` used to check Upload.created_at (upload
    recency), not the actual order data's recency -- despite the spec text
    being "Last order > 24h ago -> Show Stale Data alert". That meant
    re-uploading a file whose most recent order was months old immediately
    reported is_stale=False, and it only ever flipped True 24h after the
    *upload* itself. Regression test: an old order with a *fresh* Upload
    row must still be reported stale -- proving staleness now tracks the
    order, not the upload."""
    merchant_id = uuid.uuid4()
    old_order_date = datetime.now(timezone.utc) - timedelta(days=180)
    db_session.add(_make_order(merchant_id, old_order_date, "1000000.00"))
    # A brand new Upload row -- under the old (buggy) logic this alone was
    # enough to make is_stale report False.
    db_session.add(Upload(id=uuid.uuid4(), merchant_id=merchant_id, analyzer_type=AnalyzerType.ecommerce))
    await db_session.commit()

    data_from, data_to = old_order_date.date(), old_order_date.date()
    data, _, _ = await compute_dashboard_summary(db_session, merchant_id, data_from, data_to)

    assert data["data_freshness"]["last_synced"] is not None
    assert data["data_freshness"]["is_stale"] is True


async def test_data_freshness_with_a_real_recent_order_is_not_stale(db_session):
    """This is the first test to exercise the real
    datetime.now(timezone.utc) - last_order_date subtraction against an
    actual DB-retrieved timestamp -- which on SQLite comes back naive
    (tzinfo stripped), and would crash without the defensive fix."""
    merchant_id = uuid.uuid4()
    recent_order_date = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.add(_make_order(merchant_id, recent_order_date, "1000000.00"))
    await db_session.commit()

    data, _, _ = await compute_dashboard_summary(
        db_session, merchant_id, recent_order_date.date(), recent_order_date.date()
    )

    assert data["data_freshness"]["last_synced"] is not None
    assert data["data_freshness"]["is_stale"] is False
