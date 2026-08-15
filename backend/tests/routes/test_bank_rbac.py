"""RBAC tests for Bank (task 5.3) — real `UserMerchantRole` rows, real
enforcement, no bypass. Uses `rbac_client`/`as_user()` from conftest.py,
not the `client` fixture (which bypasses RBAC for the existing, pre-5.3
functional test suite)."""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.models.accounts import Account
from app.models.auth import User
from app.models.bank_transactions import BankTransaction, BankTransactionDataSource, TransactionType
from app.models.user_merchant_roles import BankRole, UserMerchantRole, Vertical
from tests.conftest import as_user


def _make_user(user_id: int) -> User:
    # premium: this suite tests RBAC (role), not plan-tier gating — see
    # test_bank_plan_gating.py for the latter.
    return User(
        id=user_id, email=f"user{user_id}@example.com", first_name="Test", last_name="User", is_verified=True,
        subscription_tier="premium",
    )


async def _grant_role(db_session, user_id: int, merchant_id, role: str) -> None:
    db_session.add(
        UserMerchantRole(id=uuid.uuid4(), user_id=user_id, merchant_id=merchant_id, vertical=Vertical.bank, role=role)
    )
    await db_session.commit()


async def _make_account_with_fraud_flag(db_session, merchant_id) -> Account:
    """4 months of stable salary/rent (enough for income-stability/ABM/
    loan-readiness to produce real results) plus one deliberately large,
    lone transaction guaranteed to trigger a real z_score_anomaly flag —
    so the "Loan Officer never sees transaction-level detail" test has a
    real flag to actually redact, not a vacuous pass because none existed."""
    account = Account(id=uuid.uuid4(), user_id=merchant_id, account_number_hash="b" * 64, bank_name="GTBank")
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
        balance -= 12000000
        rows.append(
            BankTransaction(
                id=uuid.uuid4(), account_id=account.id, transaction_date=d + timedelta(days=2), amount=-12000000,
                original_currency="NGN", type=TransactionType.debit, balance_after=balance,
                payee_normalized="Landlord Rent", data_source=BankTransactionDataSource.generic_csv,
            )
        )
    balance -= 900000000
    rows.append(
        BankTransaction(
            id=uuid.uuid4(), account_id=account.id, transaction_date=date(2026, 4, 10), amount=-900000000,
            original_currency="NGN", type=TransactionType.debit, balance_after=balance,
            payee_normalized="Suspicious One-Off Vendor", data_source=BankTransactionDataSource.generic_csv,
        )
    )
    db_session.add_all(rows)
    await db_session.commit()
    return account


# ── DIAGNOSTIC_ROLES group: dashboard/summary — full-data roles only.
# 3.4: dashboard/summary exposes top_payees_by_outflow/top_income_sources
# (real payee names) and opening/closing balances (real amounts), so Loan
# Officer must NOT be in this group — see test_loan_officer_denied_dashboard_summary
# below, alongside the other transaction-detail-bearing endpoints. ──


async def test_bank_owner_can_read(rbac_client, db_session):
    merchant_id = uuid.uuid4()
    account = await _make_account_with_fraud_flag(db_session, merchant_id)
    user = _make_user(301)
    await _grant_role(db_session, user.id, merchant_id, BankRole.bank_owner.value)
    as_user(user)

    response = await rbac_client.get(f"/api/v1/bank/dashboard/summary?account_id={account.id}")
    assert response.status_code == 200


async def test_bank_admin_can_read(rbac_client, db_session):
    merchant_id = uuid.uuid4()
    account = await _make_account_with_fraud_flag(db_session, merchant_id)
    user = _make_user(302)
    await _grant_role(db_session, user.id, merchant_id, BankRole.bank_admin.value)
    as_user(user)

    response = await rbac_client.get(f"/api/v1/bank/dashboard/summary?account_id={account.id}")
    assert response.status_code == 200


async def test_loan_officer_denied_dashboard_summary(rbac_client, db_session):
    merchant_id = uuid.uuid4()
    account = await _make_account_with_fraud_flag(db_session, merchant_id)
    user = _make_user(303)
    await _grant_role(db_session, user.id, merchant_id, BankRole.loan_officer.value)
    as_user(user)

    response = await rbac_client.get(f"/api/v1/bank/dashboard/summary?account_id={account.id}")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_bank_viewer_can_read(rbac_client, db_session):
    merchant_id = uuid.uuid4()
    account = await _make_account_with_fraud_flag(db_session, merchant_id)
    user = _make_user(304)
    await _grant_role(db_session, user.id, merchant_id, BankRole.bank_viewer.value)
    as_user(user)

    response = await rbac_client.get(f"/api/v1/bank/dashboard/summary?account_id={account.id}")
    assert response.status_code == 200


# ── No role at all for this merchant: denied ──


async def test_user_with_no_role_for_merchant_is_denied(rbac_client, db_session):
    merchant_id = uuid.uuid4()
    account = await _make_account_with_fraud_flag(db_session, merchant_id)
    user = _make_user(305)
    as_user(user)  # no UserMerchantRole row granted at all

    response = await rbac_client.get(f"/api/v1/bank/dashboard/summary?account_id={account.id}")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


# ── fraud-risk's role-specific redaction ──


async def test_bank_owner_sees_full_fraud_risk_detail(rbac_client, db_session):
    merchant_id = uuid.uuid4()
    account = await _make_account_with_fraud_flag(db_session, merchant_id)
    user = _make_user(306)
    await _grant_role(db_session, user.id, merchant_id, BankRole.bank_owner.value)
    as_user(user)

    response = await rbac_client.get(f"/api/v1/bank/predictive/fraud-risk?account_id={account.id}")
    assert response.status_code == 200
    flags = response.json()["data"]["flags"]
    assert len(flags) >= 1
    assert any("transaction_id" in flag for flag in flags)


async def test_bank_admin_sees_full_fraud_risk_detail(rbac_client, db_session):
    merchant_id = uuid.uuid4()
    account = await _make_account_with_fraud_flag(db_session, merchant_id)
    user = _make_user(307)
    await _grant_role(db_session, user.id, merchant_id, BankRole.bank_admin.value)
    as_user(user)

    response = await rbac_client.get(f"/api/v1/bank/predictive/fraud-risk?account_id={account.id}")
    assert response.status_code == 200
    flags = response.json()["data"]["flags"]
    assert any("transaction_id" in flag for flag in flags)


async def test_loan_officer_fraud_risk_excludes_transaction_detail(rbac_client, db_session):
    """The task's central concern."""
    merchant_id = uuid.uuid4()
    account = await _make_account_with_fraud_flag(db_session, merchant_id)
    user = _make_user(308)
    await _grant_role(db_session, user.id, merchant_id, BankRole.loan_officer.value)
    as_user(user)

    response = await rbac_client.get(f"/api/v1/bank/predictive/fraud-risk?account_id={account.id}")
    assert response.status_code == 200
    flags = response.json()["data"]["flags"]
    assert len(flags) >= 1  # sanity: real flags exist, redaction isn't vacuous
    for flag in flags:
        assert "transaction_id" not in flag
        assert "amount" not in flag
        assert "description" not in flag


async def test_bank_viewer_fraud_risk_excludes_transaction_detail(rbac_client, db_session):
    merchant_id = uuid.uuid4()
    account = await _make_account_with_fraud_flag(db_session, merchant_id)
    user = _make_user(309)
    await _grant_role(db_session, user.id, merchant_id, BankRole.bank_viewer.value)
    as_user(user)

    response = await rbac_client.get(f"/api/v1/bank/predictive/fraud-risk?account_id={account.id}")
    assert response.status_code == 200
    flags = response.json()["data"]["flags"]
    for flag in flags:
        assert "transaction_id" not in flag
        assert "amount" not in flag
        assert "description" not in flag


# ── The task's explicit second test: Loan Officer's response from EVERY bank
# endpoint excludes transaction-level fields, not just fraud-risk ──


async def test_loan_officer_response_excludes_transaction_level_fields_from_every_endpoint(
    rbac_client, db_session, monkeypatch
):
    async def fake_generate_text(prompt, **kwargs):
        return "[]"

    monkeypatch.setattr("app.services.recommendation_generation.generate_text", fake_generate_text)

    merchant_id = uuid.uuid4()
    account = await _make_account_with_fraud_flag(db_session, merchant_id)
    user = _make_user(310)
    await _grant_role(db_session, user.id, merchant_id, BankRole.loan_officer.value)
    as_user(user)

    # 3.4: dashboard/summary is intentionally excluded here — it carries real
    # payee names and balances, so it belongs in the denied-paths list below,
    # not the brief-only endpoints a Loan Officer may actually reach.
    endpoints = [
        "/api/v1/bank/predictive/fraud-risk",
        "/api/v1/bank/predictive/loan-readiness",
        "/api/v1/bank/ai/lender-brief",
    ]

    for path in endpoints:
        response = await rbac_client.get(f"{path}?account_id={account.id}")
        assert response.status_code == 200, f"{path} returned {response.status_code}"
        # transaction_id is what actually distinguishes "a specific
        # transaction record" from a legitimate aggregate bucket.
        assert '"transaction_id"' not in response.text, f"{path} leaked a raw transaction_id"


async def test_loan_officer_is_denied_transaction_level_diagnostics_and_financial_health_playbook(
    rbac_client, db_session,
):
    merchant_id = uuid.uuid4()
    account = await _make_account_with_fraud_flag(db_session, merchant_id)
    user = _make_user(311)
    await _grant_role(db_session, user.id, merchant_id, BankRole.loan_officer.value)
    as_user(user)

    denied_paths = [
        # 3.4: dashboard/summary exposes top_payees_by_outflow/
        # top_income_sources (real payee names) and opening/closing balances
        # (real amounts) -- both explicitly off-limits for Loan Officer.
        "/api/v1/bank/dashboard/summary",
        "/api/v1/bank/diagnostic/income-stability",
        "/api/v1/bank/diagnostic/abm",
        "/api/v1/bank/diagnostic/cashflow-analysis",
        "/api/v1/bank/predictive/cashflow-forecast",
        "/api/v1/bank/ai/financial-health-playbook",
    ]

    for path in denied_paths:
        response = await rbac_client.get(f"{path}?account_id={account.id}")
        assert response.status_code == 403, f"{path} should be blocked for loan_officer"
        assert response.json()["error"]["code"] == "FORBIDDEN"


# ── 3.9: authorization must run before any account-scoped read/write ──


async def test_unauthorized_account_id_never_triggers_the_transfer_scan_write(rbac_client, db_session, monkeypatch):
    """The concrete defect 3.9 fixes: `_load_account_and_transactions` used
    to load the account, run the own-account-transfer scan (a WRITE --
    `detect_own_account_transfers`), and load every transaction BEFORE
    `check_role` was ever called in the route body. An authenticated user
    with no role at all for this account's merchant could trigger that scan
    just by guessing a valid `account_id`. `require_account_role`
    (merchant_dependencies.py) now resolves and validates the account BEFORE
    the handler body -- and only the handler body calls `_load_transactions`
    (the function that actually runs the scan)."""
    scan_calls = []

    async def _fake_detect_own_account_transfers(db, user_id, *args, **kwargs):
        scan_calls.append(user_id)
        return 0

    monkeypatch.setattr(
        "app.routes.bank.detect_own_account_transfers", _fake_detect_own_account_transfers
    )

    merchant_id = uuid.uuid4()
    account = await _make_account_with_fraud_flag(db_session, merchant_id)
    outsider = _make_user(312)
    as_user(outsider)  # no UserMerchantRole row for this merchant at all

    response = await rbac_client.get(f"/api/v1/bank/dashboard/summary?account_id={account.id}")

    assert response.status_code == 403
    assert scan_calls == []  # the write never ran for the unauthorized caller


async def test_authorized_account_id_still_triggers_the_transfer_scan_write(rbac_client, db_session, monkeypatch):
    """Sanity counterpart to the test above: the scan must still run for a
    genuinely authorized caller -- proves the fix denies unauthorized
    writes without breaking the real feature (audit #21) for authorized
    ones."""
    scan_calls = []

    async def _fake_detect_own_account_transfers(db, user_id, *args, **kwargs):
        scan_calls.append(user_id)
        return 0

    monkeypatch.setattr(
        "app.routes.bank.detect_own_account_transfers", _fake_detect_own_account_transfers
    )

    merchant_id = uuid.uuid4()
    account = await _make_account_with_fraud_flag(db_session, merchant_id)
    owner = _make_user(313)
    await _grant_role(db_session, owner.id, merchant_id, BankRole.bank_owner.value)
    as_user(owner)

    response = await rbac_client.get(f"/api/v1/bank/dashboard/summary?account_id={account.id}")

    assert response.status_code == 200
    assert scan_calls == [merchant_id]
