"""Task 5.6: a basic-tier user gets a clear "upgrade required" response
(standard error envelope shape) on premium-gated health-score components;
a premium-tier user doesn't."""

from app.dependencies import get_current_user
from app.main import app
from app.models.auth import User

# Triggers dataset_type=="sales" via DATASET_SIGNATURES keyword matching
# (deal/pipeline/stage/win/rep) -- _health_sales scores "Win Rate" (basic)
# and "Churn Risk Score" (premium).
_SALES_CSV = (
    b"deal_id,pipeline_stage,rep,win,amount\n"
    b"1,Closed Won,Alice,True,100000\n"
    b"2,Closed Lost,Bob,False,50000\n"
    b"3,Closed Won,Alice,True,75000\n"
)


def _client_as(db_session_factory, subscription_tier: str):
    from fastapi.testclient import TestClient
    from app.database import get_db

    user = User(id=1, email="tier-test@example.com", first_name="Test", last_name="User", is_verified=True, subscription_tier=subscription_tier)

    async def _override_get_db():
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)
    return client


def test_basic_tier_user_gets_locked_premium_components(db_session_factory):
    client = _client_as(db_session_factory, "basic")
    try:
        response = client.post("/api/analyze", files={"file": ("deals.csv", _SALES_CSV, "text/csv")})

        assert response.status_code == 200
        body = response.json()
        components = body["health_score"]["components"]
        by_name = {c["name"]: c for c in components}

        win_rate = by_name["Win Rate"]
        assert win_rate.get("locked") is not True  # basic component, untouched
        assert "score" in win_rate

        churn = by_name["Churn Risk Score"]
        assert churn["locked"] is True
        assert churn["upgrade_required"] is True
        assert churn["error"]["code"] == "UPGRADE_REQUIRED"
        assert "score" not in churn  # the real value must not leak through
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        from app.database import get_db
        app.dependency_overrides.pop(get_db, None)


def test_premium_tier_user_sees_all_components_unlocked(db_session_factory):
    client = _client_as(db_session_factory, "premium")
    try:
        response = client.post("/api/analyze", files={"file": ("deals.csv", _SALES_CSV, "text/csv")})

        assert response.status_code == 200
        body = response.json()
        components = body["health_score"]["components"]
        by_name = {c["name"]: c for c in components}

        churn = by_name["Churn Risk Score"]
        assert churn.get("locked") is not True
        assert "score" in churn
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        from app.database import get_db
        app.dependency_overrides.pop(get_db, None)
