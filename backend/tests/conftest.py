"""Shared fixtures for the app test suite.

`backend/conftest.py` (one level up) only registers the Celery pytest plugin
— pytest_plugins can only be declared in the rootdir conftest. Everything
app-specific (test DB, test clients) lives here instead.

Three client fixtures exist side by side intentionally:
- `client` (async, httpx) — Shoaib's convention, used across the ecommerce/bank
  schema test suite. Keep using this for new tests in that style. Since 5.1/5.2
  added real RBAC to ecommerce/bank routes, this fixture auto-authenticates as a
  fixed fixture user AND bypasses the merchant-role lookup (always full access) —
  these ~90 existing tests are about business logic, not RBAC, and weren't written
  with auth in mind. Real RBAC enforcement is exercised by `rbac_client` instead.
- `rbac_client` (async, httpx) — for tests in test_ecommerce_rbac.py/test_bank_rbac.py
  only. No bypass: seed real `UserMerchantRole` rows and switch identity per-request
  with `as_user()`.
- `sync_client` / `authenticated_client` (sync, starlette TestClient) — Shakir's
  convention, used by the Phase 0 infra tests. `authenticated_client` additionally
  overrides `get_current_user`, for hitting protected routes without running the
  full register/login/OTP flow first.
"""
import asyncio
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.dependencies import get_current_user
from app.main import app
from app.models import BankRole, Base, EcommerceRole, User, Vertical


@pytest.fixture(autouse=True)
def _no_real_emails(monkeypatch):
    """Never let a test send a real email. `.env` may have real Resend
    credentials configured for local dev — without this, a test exercising
    register/login/password-reset would actually call the Resend API."""

    async def _noop(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr("app.utils.email._send", _noop)


@pytest.fixture(autouse=True)
def _no_real_payment_provider_calls(monkeypatch):
    """Never let a test hit a real payment provider. `.env` may have a real
    Paystack/Flutterwave secret key configured for local dev/manual smoke
    testing — without this, any test exercising checkout that doesn't
    explicitly mock the provider (most don't; that's the point of the
    fallback/idempotency tests, which mock deliberately) would make a real
    network call against a live account instead of staying isolated. A test
    that wants a provider "configured" sets these itself via its own
    monkeypatch, which layers on top of this one fine."""
    monkeypatch.setattr("app.config.settings.paystack_secret_key", "")
    monkeypatch.setattr("app.config.settings.paystack_basic_plan_code", "")
    monkeypatch.setattr("app.config.settings.paystack_premium_plan_code", "")
    monkeypatch.setattr("app.config.settings.flutterwave_secret_key", "")
    monkeypatch.setattr("app.config.settings.flutterwave_basic_plan_id", "")
    monkeypatch.setattr("app.config.settings.flutterwave_premium_plan_id", "")
    monkeypatch.setattr("app.config.settings.flutterwave_webhook_secret_hash", "")


@pytest.fixture(autouse=True)
def _no_real_fx_rate_calls(monkeypatch):
    """Never let a test hit the real live FX rate API (app.services.fx_rates
    — a public, keyless endpoint, so unlike Paystack/Flutterwave there's no
    settings flag to blank out; the network call itself is mocked instead).
    Returns a fixed, deterministic test rate so any test exercising checkout
    pricing gets reproducible numbers instead of whatever USD/NGN happens to
    be today."""

    async def _fixed_rate() -> Decimal:
        return 150000

    monkeypatch.setattr("app.services.fx_rates.fetch_live_usd_ngn_rate", _fixed_rate)


@pytest.fixture(autouse=True)
def _reset_shared_process_state():
    """The per-IP auth rate limiter and the OAuth-state/OTP-lockout/
    provisioning-lock helpers (app/services/redis_client.py) all fall back
    to one process-wide in-memory store when Redis isn't reachable — which
    it isn't in this test environment. Without resetting it between tests,
    state accumulates across the whole pytest run (e.g. the rate limiter's
    request counter), so enough auth-route tests in one session start
    tripping 429s that have nothing to do with what any individual test is
    checking. Runs before *and* after each test so state never leaks either
    direction."""
    from app.services.redis_client import redis_client

    redis_client._fallback._values.clear()
    redis_client._fallback._counters.clear()
    yield
    redis_client._fallback._values.clear()
    redis_client._fallback._counters.clear()


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with test_session() as session:
        yield session

    await engine.dispose()


_FIXTURE_USER = User(
    id=1,
    email="fixture-user@example.com",
    first_name="Test",
    last_name="User",
    is_verified=True,
    # This suite predates plan-tier gating (plan_permissions.py) and exists
    # to test RBAC/functional behavior, not plan access — premium keeps
    # every gated endpoint reachable so those tests aren't accidentally
    # asserting on a 403 they were never written to expect.
    subscription_tier="premium",
)


@pytest.fixture
async def client(db_session, monkeypatch):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: _FIXTURE_USER

    async def _bypass_get_merchant_role(db, user_id, merchant_id, vertical):
        role = EcommerceRole.owner.value if vertical == Vertical.ecommerce else BankRole.bank_owner.value
        return SimpleNamespace(user_id=user_id, merchant_id=merchant_id, vertical=vertical, role=role, rep_id=None)

    monkeypatch.setattr("app.services.rbac.get_merchant_role", _bypass_get_merchant_role)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def rbac_client(db_session):
    """For real RBAC tests only — no auth/role bypass. Seed real
    `UserMerchantRole` rows via `db_session`, then call `as_user(user)`
    before each request to set which user is "logged in"."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def as_user(user: User) -> None:
    """Sets which user `rbac_client` requests are authenticated as. Call
    again with a different user to switch identity mid-test (needed for
    the adversarial cross-rep test)."""
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.fixture()
def test_db_path(tmp_path):
    """Path to an isolated per-test SQLite file — never the shared dev app.db."""
    return tmp_path / "test.db"


@pytest.fixture()
def test_db_engine(test_db_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{test_db_path}")

    async def _create_schema() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create_schema())
    yield engine
    asyncio.run(engine.dispose())


@pytest.fixture()
def db_session_factory(test_db_engine):
    return sessionmaker(test_db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture()
def sync_client(db_session_factory):
    """Unauthenticated, synchronous TestClient wired to an isolated test DB.
    Use this for routes that don't require auth (e.g. register, login)."""

    async def _override_get_db():
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def test_user() -> User:
    return User(
        id=1,
        email="fixture-user@example.com",
        first_name="Test",
        last_name="User",
        is_verified=True,
    )


@pytest.fixture()
def authenticated_client(db_session_factory, test_user):
    """Synchronous TestClient with both the test DB and auth overridden, so
    protected routes can be hit directly without going through register/
    login/OTP first."""

    async def _override_get_db():
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: test_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)
