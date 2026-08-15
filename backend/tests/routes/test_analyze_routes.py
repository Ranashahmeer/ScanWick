"""Smoke test for app/routes/analyze.py — locks in the response shape of the
core analyze endpoint so future changes don't silently break it. Storage and
encryption side effects are covered separately in test_analyze_storage.py and
test_bank_account_encryption.py."""

_CSV_BYTES = (
    b"date,category,amount,customer\n"
    b"2026-01-01,Widgets,100,Acme Co\n"
    b"2026-01-02,Gadgets,250,Globex Inc\n"
    b"2026-01-03,Widgets,175,Acme Co\n"
)


def test_analyze_csv_smoke(authenticated_client):
    response = authenticated_client.post(
        "/api/analyze",
        files={"file": ("sales.csv", _CSV_BYTES, "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()

    # stable top-level keys analyze_data() always returns, regardless of
    # detected dataset type — this is what "locks in current behavior" means
    for key in ("total_rows", "columns", "dataset_type", "data_quality", "health_score"):
        assert key in body, f"expected {key!r} in analyze response"

    assert body["total_rows"] == 3
    assert body["columns"] == ["date", "category", "amount", "customer"]
    assert isinstance(body["data_quality"], dict) and "score" in body["data_quality"]
    assert isinstance(body["health_score"], dict) and "score" in body["health_score"]


def test_analyze_rejects_non_csv(authenticated_client):
    response = authenticated_client.post(
        "/api/analyze",
        files={"file": ("photo.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )

    assert response.status_code == 415


def test_analyze_rejects_empty_csv(authenticated_client):
    response = authenticated_client.post(
        "/api/analyze",
        files={"file": ("empty.csv", b"col_a,col_b\n", "text/csv")},
    )

    assert response.status_code == 422
