import time

from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import app
from app.models.auth import User

_TIMEOUT_SECONDS = 10


def test_ping_task_round_trips_through_celery(celery_worker):
    """Calls the ping endpoint with a real worker consuming from real Redis,
    proving the broker, worker, and result backend all work end-to-end.

    Audit #11: this endpoint had no auth at all; now requires any
    authenticated user, so this test overrides get_current_user the same
    way every other route test does rather than hitting a real login flow —
    this test is about the Celery/Redis round-trip, not auth itself."""
    fixture_user = User(id=1, email="ping-task-test@example.com", first_name="Test", last_name="User", is_verified=True)
    app.dependency_overrides[get_current_user] = lambda: fixture_user
    try:
        with TestClient(app) as client:
            start = time.monotonic()
            response = client.post("/api/internal/ping-task")
            elapsed = time.monotonic() - start
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert elapsed < _TIMEOUT_SECONDS, f"ping_task took too long to round-trip: {elapsed:.2f}s"
    assert response.status_code == 200
    body = response.json()
    assert body["task_id"]
    assert body["result"] == {"message": "pong"}
