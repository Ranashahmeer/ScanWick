from pathlib import Path
from urllib.parse import urlparse

from app.config import settings
from app.services.storage import get_file_url


def test_analyze_persists_csv_and_produces_retrievable_url(authenticated_client):
    """POST /api/analyze should persist the raw upload to storage (in addition
    to its existing analysis response), and the resulting URL should actually
    be fetchable and return the original bytes."""
    csv_bytes = b"amount,category\n100,Widgets\n200,Gadgets\n"
    analyze_dir = Path(settings.local_storage_dir) / "analyze"
    before = set(analyze_dir.glob("*")) if analyze_dir.exists() else set()

    try:
        response = authenticated_client.post(
            "/api/analyze",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
        )
        assert response.status_code == 200
        # existing response behavior is untouched — still just the analysis result
        assert "error" not in response.json()

        after = set(analyze_dir.glob("*"))
        new_files = after - before
        assert len(new_files) == 1, "expected exactly one new file persisted to storage"
        stored_file = new_files.pop()
        assert stored_file.read_bytes() == csv_bytes

        key = f"analyze/{stored_file.name}"
        url = get_file_url(key)
        fetch_response = authenticated_client.get(urlparse(url).path)

        assert fetch_response.status_code == 200
        assert fetch_response.content == csv_bytes
    finally:
        for f in analyze_dir.glob("*"):
            if f not in before:
                f.unlink(missing_ok=True)
