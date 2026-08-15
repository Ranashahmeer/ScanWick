import uuid

from app.services import storage as storage_module
from app.services.bank_pdf_ingestion import ingest_bank_pdf
from app.services.mono_client import MonoAPIError
from app.services.storage import LocalFileStorage
from app.services.upload_staging import read_staged_bytes


async def test_upload_bank_pdf_dispatches_ingestion(client, tmp_path, monkeypatch):
    dispatched = {}
    monkeypatch.setattr(
        ingest_bank_pdf, "delay", lambda upload_id, merchant_id, bank_name: dispatched.update(
            upload_id=upload_id, bank_name=bank_name
        )
    )
    # Isolates this test's staged file from real dev storage — same
    # LocalFileStorage the app uses by default, just pointed at a temp dir.
    monkeypatch.setattr(storage_module, "storage", LocalFileStorage(base_dir=str(tmp_path), base_url="http://test"))

    fields = {"merchant_id": str(uuid.uuid4()), "bank_name": "GTBank"}
    files = {"file": ("statement.pdf", b"%PDF-1.4 fake pdf bytes", "application/pdf")}

    response = await client.post("/api/v1/bank/upload/pdf", data=fields, files=files)

    assert response.status_code == 202
    body = response.json()
    assert body["data"]["status"] == "processing"
    assert dispatched["upload_id"] == body["data"]["upload_id"]
    assert dispatched["bank_name"] == "GTBank"
    assert read_staged_bytes(body["data"]["upload_id"], "pdf") == b"%PDF-1.4 fake pdf bytes"


async def test_upload_bank_pdf_rejects_non_pdf_file(client):
    fields = {"merchant_id": str(uuid.uuid4())}
    files = {"file": ("statement.csv", b"not a pdf", "text/csv")}

    response = await client.post("/api/v1/bank/upload/pdf", data=fields, files=files)

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


async def test_upload_bank_mono_returns_ingestion_result(client, monkeypatch):
    async def _fake_ingest(db, merchant_id, mono_account_id):
        return {"account_id": str(uuid.uuid4()), "transactions_created": 12, "rows_rejected": 0}

    monkeypatch.setattr("app.routes.bank.ingest_mono_account", _fake_ingest)
    monkeypatch.setattr("app.routes.bank.settings.mono_secret_key", "test-secret")

    response = await client.post(
        "/api/v1/bank/upload/mono",
        json={"merchant_id": str(uuid.uuid4()), "mono_account_id": "acc_ng_1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["transactions_created"] == 12


async def test_upload_bank_mono_returns_503_when_not_configured(client, monkeypatch):
    monkeypatch.setattr("app.routes.bank.settings.mono_secret_key", "")

    response = await client.post(
        "/api/v1/bank/upload/mono",
        json={"merchant_id": str(uuid.uuid4()), "mono_account_id": "acc_ng_1"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "MONO_NOT_CONFIGURED"


async def test_upload_bank_mono_returns_502_on_mono_api_error(client, monkeypatch):
    async def _fake_ingest(db, merchant_id, mono_account_id):
        raise MonoAPIError("Mono returned 401")

    monkeypatch.setattr("app.routes.bank.ingest_mono_account", _fake_ingest)
    monkeypatch.setattr("app.routes.bank.settings.mono_secret_key", "test-secret")

    response = await client.post(
        "/api/v1/bank/upload/mono",
        json={"merchant_id": str(uuid.uuid4()), "mono_account_id": "acc_ng_1"},
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "MONO_API_ERROR"
