import io
import uuid
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models.orders import Order
from app.models.uploads import Upload, UploadStatus
from app.services import ecommerce_ingestion
from app.services.ecommerce_ingestion import ingest_ecommerce_csv
from app.services.upload_staging import delete_staged_upload, stage_upload


@pytest.fixture
async def staged_upload(monkeypatch, tmp_path):
    """Stages a sample CSV at the path the task expects for a given upload_id,
    and points the task's DB session at an isolated temp-file engine instead
    of the real dev app.db (the task uses app.database.async_session
    directly, not the test db_session fixture, since Celery tasks have no
    request-scoped dependency injection)."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/task_test.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    test_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(ecommerce_ingestion, "async_session", test_session)

    upload_id = str(uuid.uuid4())
    fixture = Path(__file__).parent.parent / "fixtures" / "shopify_sample.csv"
    stage_upload(upload_id, fixture.read_bytes(), "csv")

    yield upload_id, test_session

    delete_staged_upload(upload_id)
    await engine.dispose()


def test_ingest_ecommerce_csv_task_called_directly(staged_upload):
    """Sync on purpose: the task internally calls asyncio.run(), exactly like
    a real Celery worker would (no event loop already running). Calling it
    from an async test function would conflict with that."""
    upload_id, test_session = staged_upload
    merchant_id = str(uuid.uuid4())

    # Calling the task directly (not .delay()/.apply_async()) runs it
    # synchronously in-process — no broker needed.
    result = ingest_ecommerce_csv(upload_id, merchant_id, source="shopify_csv")

    assert result["orders_created"] == 3
    assert result["items_created"] == 3
    assert result["rows_rejected"] == 0
    assert result["quality_report"]["rows_parsed"] == 3

    async def _check():
        async with test_session() as db:
            orders = (
                (await db.execute(select(Order).where(Order.merchant_id == uuid.UUID(merchant_id)))).scalars().all()
            )
            upload = (await db.execute(select(Upload).where(Upload.id == uuid.UUID(upload_id)))).scalar_one()
            return orders, upload

    import asyncio

    orders, upload = asyncio.run(_check())
    assert len(orders) == 3
    assert upload.status == UploadStatus.ready
    assert upload.rows_parsed == 3
    assert upload.rows_rejected == 0


def test_ingest_ecommerce_csv_task_quality_report_surfaces_duplicates_and_rejected_reasons(staged_upload):
    """3.6: the quality report must name WHY rows didn't land as new orders,
    not just how many -- rejected_reasons breaks down the NOT-NULL rejection
    causes, and a re-run against the same staged data (same merchant, same
    file) must both report a duplicates_skipped count and carry a named
    warning explaining it, not just a silent lower orders_created."""
    upload_id, test_session = staged_upload
    merchant_id = str(uuid.uuid4())

    first = ingest_ecommerce_csv(upload_id, merchant_id, source="shopify_csv")
    assert first["quality_report"]["rejected_reasons"] == {"missing_gross_revenue": 0, "missing_order_date": 0}
    assert first["quality_report"]["duplicates_skipped"] == 0

    # Re-stage the identical file under a second upload_id for the same
    # merchant -- simulates a client retry / re-upload of the same export.
    second_upload_id = str(uuid.uuid4())
    fixture = Path(__file__).parent.parent / "fixtures" / "shopify_sample.csv"
    stage_upload(second_upload_id, fixture.read_bytes(), "csv")
    try:
        second = ingest_ecommerce_csv(second_upload_id, merchant_id, source="shopify_csv")
    finally:
        delete_staged_upload(second_upload_id)

    assert second["orders_created"] == 0
    assert second["duplicates_skipped"] == 3
    assert second["quality_report"]["duplicates_skipped"] == 3
    assert any(w["field"] == "external_order_id" for w in second["quality_report"]["warnings"])


@pytest.fixture
async def staged_xlsx_upload(monkeypatch, tmp_path):
    """Same as staged_upload, but stages the same Shopify sample data as an
    .xlsx file instead of .csv -- proves the ingestion task works end-to-end
    on a real XLSX upload, not just CSV."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/task_test_xlsx.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    test_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(ecommerce_ingestion, "async_session", test_session)

    upload_id = str(uuid.uuid4())
    csv_fixture = Path(__file__).parent.parent / "fixtures" / "shopify_sample.csv"
    buf = io.BytesIO()
    pd.read_csv(csv_fixture).to_excel(buf, index=False)
    stage_upload(upload_id, buf.getvalue(), "xlsx")

    yield upload_id, test_session

    delete_staged_upload(upload_id)
    await engine.dispose()


def test_ingest_ecommerce_csv_task_accepts_xlsx_upload(staged_xlsx_upload):
    upload_id, test_session = staged_xlsx_upload
    merchant_id = str(uuid.uuid4())

    result = ingest_ecommerce_csv(upload_id, merchant_id, source="shopify_csv")

    assert result["orders_created"] == 3
    assert result["items_created"] == 3
    assert result["rows_rejected"] == 0

    async def _check():
        async with test_session() as db:
            return (
                (await db.execute(select(Order).where(Order.merchant_id == uuid.UUID(merchant_id)))).scalars().all()
            )

    import asyncio

    orders = asyncio.run(_check())
    assert len(orders) == 3
