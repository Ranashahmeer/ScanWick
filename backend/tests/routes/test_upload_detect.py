from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


async def test_detect_upload_type_identifies_a_bank_statement(client):
    files = {"file": ("statement.csv", (FIXTURES_DIR / "generic_bank_sample.csv").read_bytes(), "text/csv")}

    response = await client.post("/api/v1/upload/detect", files=files)

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["analyzer_type"] == "bank"
    assert body["source"] is None
    assert body["confidence"] == 1.0


async def test_detect_upload_type_identifies_a_shopify_export(client):
    files = {"file": ("orders.csv", (FIXTURES_DIR / "shopify_sample.csv").read_bytes(), "text/csv")}

    response = await client.post("/api/v1/upload/detect", files=files)

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["analyzer_type"] == "ecommerce"
    assert body["source"] == "shopify_csv"


async def test_detect_upload_type_low_confidence_on_unrecognizable_csv(client):
    files = {"file": ("mystery.csv", b"foo,bar\n1,2\n", "text/csv")}

    response = await client.post("/api/v1/upload/detect", files=files)

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["analyzer_type"] is None
    assert body["confidence"] < 0.4


async def test_detect_upload_type_rejects_non_csv_file(client):
    files = {"file": ("payload.exe", b"not really a csv", "application/octet-stream")}

    response = await client.post("/api/v1/upload/detect", files=files)

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


async def test_detect_upload_type_rejects_empty_file(client):
    files = {"file": ("empty.csv", b"", "text/csv")}

    response = await client.post("/api/v1/upload/detect", files=files)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "EMPTY_FILE"
