"""Plan-tier gating (Free/Basic/Premium) — the enforcement side of
app/services/plan_permissions.py. RBAC (role-within-a-merchant) is
bypassed the same way the `client` fixture already bypasses it for the
pre-existing functional suite (every role resolves to "owner") — these
tests are only about `check_feature_access`, not `check_role`."""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import User
from app.models.bank_transactions import BankTransaction, BankTransactionDataSource, TransactionType
from app.models.accounts import Account
from app.models.user_merchant_roles import BankRole, EcommerceRole, Vertical


async def _client_as_tier(db_session, monkeypatch, tier: str):
    user = User(id=1, email="tier-test@example.com", first_name="Test", last_name="User", is_verified=True, subscription_tier=tier)

    async def override_get_db():
        yield db_session

    async def _bypass_get_merchant_role(db, user_id, merchant_id, vertical):
        role = EcommerceRole.owner.value if vertical == Vertical.ecommerce else BankRole.bank_owner.value
        return SimpleNamespace(user_id=user_id, merchant_id=merchant_id, vertical=vertical, role=role, rep_id=None)

    monkeypatch.setattr("app.services.rbac.get_merchant_role", _bypass_get_merchant_role)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ── GET /api/v1/plans/permissions ───────────────────────────────────────


async def test_plan_permissions_endpoint_returns_full_matrix(db_session, monkeypatch):
    client = await _client_as_tier(db_session, monkeypatch, "free")
    async with client:
        response = await client.get("/api/v1/plans/permissions")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert "E-Commerce Analyzer" in body["data"]
    assert "Bank Statement Analyzer" in body["data"]
    net_margin_dashboard = next(
        f for f in body["data"]["E-Commerce Analyzer"] if f["key"] == "ecommerce.net_margin_dashboard"
    )
    assert net_margin_dashboard["access"]["free"]["level"] == "none"
    assert net_margin_dashboard["access"]["basic"]["level"] == "full"


# ── Plain FULL/NONE gates ────────────────────────────────────────────────


async def test_ecommerce_net_margin_dashboard_blocked_for_free(db_session, monkeypatch):
    merchant_id = uuid.uuid4()
    client = await _client_as_tier(db_session, monkeypatch, "free")
    async with client:
        response = await client.get(f"/api/v1/ecommerce/dashboard/revenue?merchant_id={merchant_id}")
    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "UPGRADE_REQUIRED"


async def test_ecommerce_net_margin_dashboard_allowed_for_basic(db_session, monkeypatch):
    merchant_id = uuid.uuid4()
    client = await _client_as_tier(db_session, monkeypatch, "basic")
    async with client:
        response = await client.get(
            f"/api/v1/ecommerce/dashboard/revenue?merchant_id={merchant_id}&date_from=2026-01-01&date_to=2026-01-31"
        )
    app.dependency_overrides.clear()

    assert response.status_code == 200


# ── bank.loan_readiness: three-way tiered (Grade only / Score+grade+tier / Full) ─


async def _seed_bank_account_with_history(db_session):
    account = Account(id=uuid.uuid4(), user_id=uuid.uuid4(), account_number_hash="p" * 64, bank_name="GTBank")
    db_session.add(account)
    await db_session.commit()

    rows = []
    balance = 100000000
    for day_base in (1, 32, 63, 94):
        d = date(2026, 1, 1) + timedelta(days=day_base - 1)
        balance += 50000000
        rows.append(
            BankTransaction(
                id=uuid.uuid4(), account_id=account.id, transaction_date=d, amount=50000000,
                original_currency="NGN", type=TransactionType.credit, balance_after=balance,
                payee_normalized="Salary Inc", data_source=BankTransactionDataSource.generic_csv,
            )
        )
    db_session.add_all(rows)
    await db_session.commit()
    return account


async def test_loan_readiness_grade_only_for_free(db_session, monkeypatch):
    account = await _seed_bank_account_with_history(db_session)

    client = await _client_as_tier(db_session, monkeypatch, "free")
    async with client:
        response = await client.get(f"/api/v1/bank/predictive/loan-readiness?account_id={account.id}")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert set(body["data"].keys()) == {"creditworthiness_tier"}
    assert body["data"]["creditworthiness_tier"] in ("A", "B", "C", "D")
    assert body["meta"]["plan_access"]["detail"] == "Grade only (A/B/C/D)"


async def test_loan_readiness_score_and_tier_for_basic(db_session, monkeypatch):
    account = await _seed_bank_account_with_history(db_session)

    client = await _client_as_tier(db_session, monkeypatch, "basic")
    async with client:
        response = await client.get(f"/api/v1/bank/predictive/loan-readiness?account_id={account.id}")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert set(body["data"].keys()) == {"loan_readiness_score", "creditworthiness_tier", "tier_definition"}
    assert body["meta"]["plan_access"]["detail"] == "Score + grade + tier"


async def test_loan_readiness_full_breakdown_for_premium(db_session, monkeypatch):
    account = await _seed_bank_account_with_history(db_session)

    client = await _client_as_tier(db_session, monkeypatch, "premium")
    async with client:
        response = await client.get(f"/api/v1/bank/predictive/loan-readiness?account_id={account.id}")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert "score_breakdown" in body["data"]
    assert "improvement_recommendations" in body["data"]


# ── bank.fraud_risk: NONE at Free, LIMITED (statement_integrity only) at Basic, FULL at Premium ─


async def test_fraud_risk_blocked_for_free(db_session, monkeypatch):
    account = await _seed_bank_account_with_history(db_session)

    client = await _client_as_tier(db_session, monkeypatch, "free")
    async with client:
        response = await client.get(f"/api/v1/bank/predictive/fraud-risk?account_id={account.id}")
    app.dependency_overrides.clear()

    assert response.status_code == 403


async def test_fraud_risk_statement_integrity_only_for_basic(db_session, monkeypatch):
    account = await _seed_bank_account_with_history(db_session)

    client = await _client_as_tier(db_session, monkeypatch, "basic")
    async with client:
        response = await client.get(f"/api/v1/bank/predictive/fraud-risk?account_id={account.id}")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert set(body["data"].keys()) == {"statement_integrity"}
    assert body["meta"]["plan_access"]["level"] == "limited"


async def test_fraud_risk_full_for_premium(db_session, monkeypatch):
    account = await _seed_bank_account_with_history(db_session)

    client = await _client_as_tier(db_session, monkeypatch, "premium")
    async with client:
        response = await client.get(f"/api/v1/bank/predictive/fraud-risk?account_id={account.id}")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert "fraud_risk_score" in body["data"]
    assert "flags" in body["data"]
    assert body["meta"]["plan_access"]["level"] == "full"
