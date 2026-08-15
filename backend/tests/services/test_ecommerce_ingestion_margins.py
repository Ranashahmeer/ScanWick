import uuid
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models.order_items import OrderItem
from app.models.orders import Order, OrderDataSource
from app.models.uploads import Upload
from app.services import ecommerce_ingestion
from app.services.ecommerce_ingestion import ingest_dataframe, ingest_ecommerce_csv
from app.services.upload_staging import delete_staged_upload, stage_upload

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


async def test_ingestion_computes_net_margin_and_unit_net_margin_end_to_end(db_session):
    """No MerchantSettings row exists, so the return-cost fallback for
    #4002/#4003 lands on the zero-default branch (no SKU override, no
    merchant default) while #4001's SKU-level override is honored."""
    merchant_id = uuid.uuid4()
    df = pd.read_csv(FIXTURES_DIR / "shopify_with_margins.csv")
    result = await ingest_dataframe(db_session, df, merchant_id, OrderDataSource.shopify_csv)

    assert result["return_cost_defaulted_count"] == 2  # #4002 and #4003

    orders = (await db_session.execute(select(Order).where(Order.merchant_id == merchant_id))).scalars().all()
    by_id = {o.external_order_id: o for o in orders}

    order_4001 = by_id["#4001"]
    assert order_4001.cogs == 80000  # unit_cogs 400 * qty 2
    assert order_4001.net_margin == 85000  # 2000 - 100 disc - 800 cogs - 150 ship - 100 return(50*2)

    order_4002 = by_id["#4002"]
    assert order_4002.cogs == 30000
    assert order_4002.net_margin == 62500  # 1000 - 300 cogs - 75 ship - 0 return (defaulted)

    order_4003 = by_id["#4003"]
    assert order_4003.cogs is None  # unit_cogs missing for this order's only item
    assert order_4003.net_margin is None  # never use gross revenue as a profitability proxy

    items = (await db_session.execute(select(OrderItem).where(OrderItem.merchant_id == merchant_id))).scalars().all()
    by_sku = {i.sku: i for i in items}

    item_a = by_sku["SKU-A"]
    assert item_a.unit_return_cost == 5000  # SKU-level override, as stored (not the resolved value)
    assert item_a.unit_net_margin == 40000  # 1000 - 400 cogs - 150 ship - 50 return

    item_b = by_sku["SKU-B"]
    assert item_b.unit_return_cost is None  # no override was provided in the source data
    assert item_b.unit_net_margin == 62500  # 1000 - 300 cogs - 75 ship - 0 (defaulted return cost)

    item_c = by_sku["SKU-C"]
    assert item_c.unit_net_margin is None  # unit_cogs unknown


@pytest.fixture
async def staged_margins_upload(monkeypatch, tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/margins_task_test.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    test_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(ecommerce_ingestion, "async_session", test_session)

    upload_id = str(uuid.uuid4())
    stage_upload(upload_id, (FIXTURES_DIR / "shopify_with_margins.csv").read_bytes(), "csv")

    yield upload_id, test_session

    delete_staged_upload(upload_id)
    await engine.dispose()


def test_missing_return_cost_warning_surfaces_on_the_upload_record(staged_margins_upload):
    upload_id, test_session = staged_margins_upload
    merchant_id = str(uuid.uuid4())

    result = ingest_ecommerce_csv(upload_id, merchant_id, source="shopify_csv")

    return_cost_warnings = [w for w in result["quality_report"]["warnings"] if w["field"] == "return_cost"]
    assert len(return_cost_warnings) == 1
    assert "2 of 3 line items" in return_cost_warnings[0]["message"]
    assert return_cost_warnings[0]["severity"] == "medium"

    import asyncio

    async def _check():
        async with test_session() as db:
            return (await db.execute(select(Upload).where(Upload.id == uuid.UUID(upload_id)))).scalar_one()

    upload = asyncio.run(_check())
    stored_warning_fields = {w["field"] for w in upload.warnings}
    assert "return_cost" in stored_warning_fields
