import uuid

from app.models.uploads import Upload, UploadStatus
from app.services.ecommerce_ingestion import ingest_ecommerce_csv
from app.services.bank_ingestion import ingest_bank_csv


async def _post_csv(client, csv_content=b"order_id,order_date,gross_revenue\n1,2026-01-01,100\n", **overrides):
    fields = {
        "analyzer_type": "ecommerce",
        "merchant_id": str(uuid.uuid4()),
        "source": "shopify_csv",
    }
    fields.update(overrides)
    files = {"file": ("orders.csv", csv_content, "text/csv")}
    return await client.post("/api/v1/upload/csv", data=fields, files=files)


async def test_upload_csv_dispatches_ecommerce_ingestion(client, db_session, monkeypatch):
    dispatched = {}
    monkeypatch.setattr(
        ingest_ecommerce_csv, "delay", lambda upload_id, merchant_id, source, mapping=None, value_rules=None: dispatched.update(
            upload_id=upload_id, merchant_id=merchant_id, source=source
        )
    )

    response = await _post_csv(client)

    assert response.status_code == 202
    body = response.json()
    assert body["success"] is True
    upload_id = body["data"]["upload_id"]
    assert body["data"]["status"] == "processing"
    assert dispatched["upload_id"] == upload_id
    assert dispatched["source"] == "shopify_csv"

    stored = await db_session.get(Upload, uuid.UUID(upload_id))
    assert stored is not None
    assert stored.status == UploadStatus.processing


async def test_upload_csv_dispatches_bank_ingestion_without_source(client, monkeypatch):
    dispatched = {}
    monkeypatch.setattr(
        ingest_bank_csv,
        "delay",
        lambda upload_id, merchant_id, bank_name, mapping=None, value_rules=None: dispatched.update(bank_name=bank_name),
    )

    response = await _post_csv(
        client,
        csv_content=b"transaction_date,description,amount,balance_after\n2026-01-01,Test,100,100\n",
        analyzer_type="bank",
        source=None,
        bank_name="GTBank",
    )

    assert response.status_code == 202
    assert dispatched["bank_name"] == "GTBank"


async def test_upload_csv_rejects_invalid_analyzer_type(client):
    response = await _post_csv(client, analyzer_type="not-a-vertical")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_ANALYZER_TYPE"


async def test_upload_csv_rejects_invalid_merchant_id(client):
    response = await _post_csv(client, merchant_id="not-a-uuid")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_MERCHANT_ID"


async def test_upload_csv_rejects_invalid_source_for_ecommerce(client):
    response = await _post_csv(client, source="not-a-real-platform")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_SOURCE"


async def test_upload_csv_rejects_non_csv_file(client):
    fields = {"analyzer_type": "ecommerce", "merchant_id": str(uuid.uuid4()), "source": "shopify_csv"}
    files = {"file": ("orders.txt", b"not a csv", "application/pdf")}

    response = await client.post("/api/v1/upload/csv", data=fields, files=files)

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


async def test_upload_csv_rejects_empty_file(client):
    fields = {"analyzer_type": "ecommerce", "merchant_id": str(uuid.uuid4()), "source": "shopify_csv"}
    files = {"file": ("orders.csv", b"", "text/csv")}

    response = await client.post("/api/v1/upload/csv", data=fields, files=files)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "EMPTY_FILE"


async def test_upload_csv_denied_for_user_without_ingest_role(db_session, rbac_client):
    from app.models.auth import User
    from app.models.user_merchant_roles import EcommerceRole, UserMerchantRole, Vertical
    from tests.conftest import as_user

    merchant_id = uuid.uuid4()
    viewer = User(id=42, email="viewer@example.com", first_name="V", last_name="User", is_verified=True)
    db_session.add(
        UserMerchantRole(
            id=uuid.uuid4(),
            user_id=viewer.id,
            merchant_id=merchant_id,
            vertical=Vertical.ecommerce,
            role=EcommerceRole.viewer.value,
        )
    )
    await db_session.commit()
    as_user(viewer)

    fields = {"analyzer_type": "ecommerce", "merchant_id": str(merchant_id), "source": "shopify_csv"}
    files = {"file": ("orders.csv", b"order_id\n1\n", "text/csv")}

    response = await rbac_client.post("/api/v1/upload/csv", data=fields, files=files)

    assert response.status_code == 403
