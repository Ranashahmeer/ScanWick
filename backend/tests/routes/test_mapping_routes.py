import uuid

from sqlalchemy import select

from app.models.column_mappings import ColumnMapping
from app.models.uploads import Upload, UploadStatus
from app.services.ecommerce_ingestion import ingest_ecommerce_csv


def _bypass_dispatch(monkeypatch):
    """Real ingestion runs against app.database's module-level session, not
    this test's isolated in-memory db_session — dispatch must be no-op'd so
    these tests only exercise the mapping-layer plumbing, not touch the
    real dev database."""
    dispatched = {}
    monkeypatch.setattr(
        ingest_ecommerce_csv,
        "delay",
        lambda upload_id, merchant_id, source, mapping=None, value_rules=None: dispatched.update(
            upload_id=upload_id, mapping=mapping, value_rules=value_rules
        ),
    )
    return dispatched


async def _post_ambiguous_csv(client, merchant_id: str):
    """'order_purchase_timestamp' fuzzy-matches order_date at a score below
    the auto-apply threshold -- genuine, real ambiguity, not contrived."""
    fields = {"analyzer_type": "ecommerce", "merchant_id": merchant_id, "source": "generic_csv"}
    files = {"file": ("orders.csv", b"order_id,order_purchase_timestamp\n1,2026-01-01\n", "text/csv")}
    return await client.post("/api/v1/upload/csv", data=fields, files=files)


async def _post_clean_csv(client, merchant_id: str):
    fields = {"analyzer_type": "ecommerce", "merchant_id": merchant_id, "source": "generic_csv"}
    files = {"file": ("orders.csv", b"order_id,order_date,gross_revenue\n1,2026-01-01,100\n", "text/csv")}
    return await client.post("/api/v1/upload/csv", data=fields, files=files)


async def test_ambiguous_upload_returns_needs_mapping_with_inline_mapping_detail(client, monkeypatch):
    _bypass_dispatch(monkeypatch)
    merchant_id = str(uuid.uuid4())

    response = await _post_ambiguous_csv(client, merchant_id)

    assert response.status_code == 202
    body = response.json()["data"]
    assert body["status"] == "needs_mapping"
    assert "mapping" in body
    assert any(n["candidate"] == "order_date" for n in body["mapping"]["needs_confirmation"])


async def test_clean_headers_auto_apply_and_dispatch_immediately(client, monkeypatch, db_session):
    dispatched = _bypass_dispatch(monkeypatch)
    merchant_id = str(uuid.uuid4())

    response = await _post_clean_csv(client, merchant_id)

    assert response.status_code == 202
    body = response.json()["data"]
    assert body["status"] == "processing"
    assert dispatched["mapping"] == {"order_id": "external_order_id", "order_date": "order_date", "gross_revenue": "gross_revenue"}

    saved = (await db_session.execute(select(ColumnMapping).where(ColumnMapping.merchant_id == uuid.UUID(merchant_id)))).scalar_one()
    assert saved.confirmed_by is None  # auto-applied, nobody confirmed it


async def test_confirm_mapping_persists_column_mapping_and_dispatches(client, monkeypatch, db_session):
    dispatched = _bypass_dispatch(monkeypatch)
    merchant_id = str(uuid.uuid4())

    upload_response = await _post_ambiguous_csv(client, merchant_id)
    upload_id = upload_response.json()["data"]["upload_id"]

    confirm_response = await client.post(
        "/api/v1/mapping/confirm",
        json={
            "upload_id": upload_id,
            "mapping": {"order_id": "external_order_id", "order_purchase_timestamp": "order_date"},
            "value_rules": {},
        },
    )

    assert confirm_response.status_code == 200
    assert confirm_response.json()["data"]["status"] == "processing"
    assert dispatched["mapping"] == {"order_id": "external_order_id", "order_purchase_timestamp": "order_date"}

    upload = await db_session.get(Upload, uuid.UUID(upload_id))
    assert upload.status == UploadStatus.processing

    saved = (
        await db_session.execute(select(ColumnMapping).where(ColumnMapping.merchant_id == uuid.UUID(merchant_id)))
    ).scalar_one()
    assert saved.confirmed_by == 1  # _FIXTURE_USER.id from conftest.py
    assert saved.mapping == {"order_id": "external_order_id", "order_purchase_timestamp": "order_date"}


async def test_repeat_upload_with_identical_headers_is_zero_touch_after_confirm(client, monkeypatch):
    dispatched = _bypass_dispatch(monkeypatch)
    merchant_id = str(uuid.uuid4())

    first = await _post_ambiguous_csv(client, merchant_id)
    upload_id = first.json()["data"]["upload_id"]
    await client.post(
        "/api/v1/mapping/confirm",
        json={
            "upload_id": upload_id,
            "mapping": {"order_id": "external_order_id", "order_purchase_timestamp": "order_date"},
            "value_rules": {"date_locale": "month_first"},
        },
    )

    second = await _post_ambiguous_csv(client, merchant_id)

    assert second.json()["data"]["status"] == "processing"  # zero-touch, no second needs_mapping round trip
    # 3.7 regression: the confirmed date_locale (and any other value_rules)
    # must still apply on a zero-touch re-upload that reuses the saved
    # mapping -- this used to be silently dropped (never forwarded to
    # _dispatch_ingestion on the auto-apply fast path).
    assert dispatched["value_rules"] == {"date_locale": "month_first"}


async def test_confirm_mapping_rejects_an_upload_not_awaiting_mapping(client, monkeypatch):
    """POST /mapping/confirm against an upload that already auto-applied
    (status=processing, never needs_mapping) must be rejected, not silently
    re-dispatch a second ingestion run."""
    _bypass_dispatch(monkeypatch)
    merchant_id = str(uuid.uuid4())

    response = await _post_clean_csv(client, merchant_id)
    upload_id = response.json()["data"]["upload_id"]

    confirm_response = await client.post(
        "/api/v1/mapping/confirm",
        json={"upload_id": upload_id, "mapping": {}, "value_rules": {}},
    )

    assert confirm_response.status_code == 409
    assert confirm_response.json()["error"]["code"] == "NOT_AWAITING_MAPPING"
