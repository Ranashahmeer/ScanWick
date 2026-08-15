import uuid
from pathlib import Path

import pandas as pd
from sqlalchemy import select

from app.models.orders import Order, OrderDataSource
from app.services.ecommerce_ingestion import ingest_dataframe, resolve_customer_id

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_resolve_customer_id_is_deterministic_per_email():
    a = resolve_customer_id("a@example.com")
    b = resolve_customer_id("a@example.com")
    assert a == b


def test_resolve_customer_id_is_case_insensitive():
    assert resolve_customer_id("A@Example.com") == resolve_customer_id("a@example.com")


def test_resolve_customer_id_differs_per_email():
    assert resolve_customer_id("a@example.com") != resolve_customer_id("b@example.com")


def test_resolve_customer_id_none_for_no_email():
    assert resolve_customer_id(None) is None
    assert resolve_customer_id("") is None


async def test_shopify_ingestion_populates_customer_id_from_email(db_session):
    """shopify_sample.csv has a real Email column — confirms customer_id is
    actually derived end-to-end through ingestion, not just unit-tested in
    isolation."""
    merchant_id = uuid.uuid4()
    df = pd.read_csv(FIXTURES_DIR / "shopify_sample.csv")
    await ingest_dataframe(db_session, df, merchant_id, OrderDataSource.shopify_csv)

    orders = (await db_session.execute(select(Order).where(Order.merchant_id == merchant_id))).scalars().all()
    assert all(o.customer_id is not None for o in orders)

    order_1001 = next(o for o in orders if o.external_order_id == "#1001")
    assert order_1001.customer_id == resolve_customer_id("a@example.com")


async def test_woocommerce_ingestion_has_no_email_column_customer_id_stays_null(db_session):
    """woocommerce_sample.csv has no billing_email column — customer_id
    stays null rather than being fabricated, an honest reflection of what
    that export actually contains."""
    merchant_id = uuid.uuid4()
    df = pd.read_csv(FIXTURES_DIR / "woocommerce_sample.csv")
    await ingest_dataframe(db_session, df, merchant_id, OrderDataSource.woocommerce_csv)

    orders = (await db_session.execute(select(Order).where(Order.merchant_id == merchant_id))).scalars().all()
    assert all(o.customer_id is None for o in orders)
