import datetime
import uuid
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy import select

from app.models.contextual_markers import ContextualMarker
from app.models.merchant_settings import MerchantSettings
from app.models.orders import Order, OrderDataSource
from app.models.reconciliation_reports import AnalyzerType
from app.services.ecommerce_ingestion import ingest_dataframe
from app.services.exchange_rates import upsert_exchange_rate

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


async def test_ingestion_converts_using_order_date_rate_not_latest(db_session):
    merchant_id = uuid.uuid4()
    db_session.add(MerchantSettings(id=uuid.uuid4(), merchant_id=merchant_id, base_currency="NGN"))
    await db_session.commit()

    # Two USD->NGN rates at different dates; the fixture's orders are dated
    # 2026-01-15/16/17, so they must use the 2026-01-01 rate, not the later one.
    await upsert_exchange_rate(db_session, "USD", "NGN", datetime.date(2025, 12, 1), 140000)
    await upsert_exchange_rate(db_session, "USD", "NGN", datetime.date(2026, 1, 1), 150000)
    await upsert_exchange_rate(db_session, "USD", "NGN", datetime.date(2026, 6, 1), 170000)

    df = pd.read_csv(FIXTURES_DIR / "shopify_sample.csv")
    df["Currency"] = "USD"  # force a real conversion instead of the NGN no-op case
    await ingest_dataframe(db_session, df, merchant_id, OrderDataSource.shopify_csv)

    orders = (await db_session.execute(select(Order).where(Order.merchant_id == merchant_id))).scalars().all()
    assert len(orders) == 3
    for order in orders:
        assert order.exchange_rate_at_order == 150000
        assert order.base_currency_amount == order.gross_revenue * 150000


async def test_ingestion_leaves_conversion_null_when_no_rate_known(db_session):
    merchant_id = uuid.uuid4()
    db_session.add(MerchantSettings(id=uuid.uuid4(), merchant_id=merchant_id, base_currency="NGN"))
    await db_session.commit()

    df = pd.read_csv(FIXTURES_DIR / "shopify_sample.csv")
    df["Currency"] = "USD"
    await ingest_dataframe(db_session, df, merchant_id, OrderDataSource.shopify_csv)

    orders = (await db_session.execute(select(Order).where(Order.merchant_id == merchant_id))).scalars().all()
    assert all(o.exchange_rate_at_order is None for o in orders)
    assert all(o.base_currency_amount is None for o in orders)


async def test_ingestion_defaults_to_orders_own_currency_when_merchant_has_no_settings_row(db_session):
    """No MerchantSettings row exists for this merchant (no onboarding done
    yet) — falls back to the order's own currency as the effective base, so
    rate=1.0 and base_currency_amount=gross_revenue rather than every order
    coming out with null conversion fields."""
    merchant_id = uuid.uuid4()

    df = pd.read_csv(FIXTURES_DIR / "shopify_sample.csv")  # NGN orders, no MerchantSettings row
    await ingest_dataframe(db_session, df, merchant_id, OrderDataSource.shopify_csv)

    orders = (await db_session.execute(select(Order).where(Order.merchant_id == merchant_id))).scalars().all()
    assert len(orders) == 3
    for order in orders:
        assert order.exchange_rate_at_order == 100
        assert order.base_currency_amount == order.gross_revenue


async def test_ingestion_flags_orders_inside_existing_marker_at_write_time(db_session):
    merchant_id = uuid.uuid4()
    db_session.add(
        ContextualMarker(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            analyzer_type=AnalyzerType.ecommerce,
            label="Promotion Period",
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 1, 16),
        )
    )
    await db_session.commit()

    df = pd.read_csv(FIXTURES_DIR / "shopify_sample.csv")
    await ingest_dataframe(db_session, df, merchant_id, OrderDataSource.shopify_csv)

    orders = (await db_session.execute(select(Order).where(Order.merchant_id == merchant_id))).scalars().all()
    by_external_id = {o.external_order_id: o for o in orders}
    assert by_external_id["#1001"].is_anomalous is True  # 2026-01-15, inside
    assert by_external_id["#1002"].is_anomalous is True  # 2026-01-16, inside (boundary)
    assert by_external_id["#1003"].is_anomalous is False  # 2026-01-17, outside
