import uuid
from datetime import date

from app.models.accounts import Account
from app.models.auth import User
from app.models.user_merchant_roles import BankRole, UserMerchantRole, Vertical
from tests.conftest import as_user


async def _make_account(db_session, merchant_id, **overrides) -> Account:
    defaults = dict(
        id=uuid.uuid4(),
        user_id=merchant_id,
        account_number_hash="a" * 64,
        bank_name="GTBank",
        base_currency="NGN",
        statement_period_start=date(2026, 1, 1),
        statement_period_end=date(2026, 3, 31),
        closing_balance=125000,
    )
    defaults.update(overrides)
    account = Account(**defaults)
    db_session.add(account)
    await db_session.commit()
    return account


async def test_list_accounts_returns_only_this_merchants_accounts(client, db_session):
    merchant_id = uuid.uuid4()
    other_merchant_id = uuid.uuid4()
    await _make_account(db_session, merchant_id, bank_name="GTBank")
    await _make_account(db_session, other_merchant_id, bank_name="Zenith Bank")

    response = await client.get("/api/v1/bank/accounts", params={"merchant_id": str(merchant_id)})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) == 1
    assert body["data"][0]["bank_name"] == "GTBank"


async def test_list_accounts_empty_for_merchant_with_no_accounts(client):
    response = await client.get("/api/v1/bank/accounts", params={"merchant_id": str(uuid.uuid4())})

    assert response.status_code == 200
    assert response.json()["data"] == []


async def test_list_accounts_rejects_invalid_merchant_id(client):
    response = await client.get("/api/v1/bank/accounts", params={"merchant_id": "not-a-uuid"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_MERCHANT_ID"


async def test_list_accounts_denied_for_user_without_a_role(db_session, rbac_client):
    merchant_id = uuid.uuid4()
    await _make_account(db_session, merchant_id)

    outsider = User(id=999, email="outsider@example.com", first_name="Out", last_name="Sider", is_verified=True)
    as_user(outsider)

    response = await rbac_client.get("/api/v1/bank/accounts", params={"merchant_id": str(merchant_id)})

    assert response.status_code == 403


async def test_list_accounts_allowed_for_bank_viewer_role(db_session, rbac_client):
    merchant_id = uuid.uuid4()
    await _make_account(db_session, merchant_id)

    viewer = User(id=42, email="viewer@example.com", first_name="View", last_name="Er", is_verified=True)
    db_session.add(
        UserMerchantRole(
            id=uuid.uuid4(), user_id=viewer.id, merchant_id=merchant_id, vertical=Vertical.bank, role=BankRole.bank_viewer.value
        )
    )
    await db_session.commit()
    as_user(viewer)

    response = await rbac_client.get("/api/v1/bank/accounts", params={"merchant_id": str(merchant_id)})

    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


async def test_list_accounts_redacts_bank_name_and_balance_for_loan_officer(db_session, rbac_client):
    """3.4: Loan Officer needs `/accounts` to obtain an account_id for the
    brief-only endpoints, but must not receive `bank_name` (account detail)
    or `closing_balance` (a real amount) — both dropped from the shape,
    while `id`/statement period (needed to identify the account) remain."""
    merchant_id = uuid.uuid4()
    account = await _make_account(db_session, merchant_id, bank_name="GTBank", closing_balance=125000)

    officer = User(id=43, email="officer@example.com", first_name="Loan", last_name="Officer", is_verified=True)
    db_session.add(
        UserMerchantRole(
            id=uuid.uuid4(), user_id=officer.id, merchant_id=merchant_id, vertical=Vertical.bank, role=BankRole.loan_officer.value
        )
    )
    await db_session.commit()
    as_user(officer)

    response = await rbac_client.get("/api/v1/bank/accounts", params={"merchant_id": str(merchant_id)})

    assert response.status_code == 200
    rows = response.json()["data"]
    assert len(rows) == 1
    assert rows[0]["id"] == str(account.id)
    assert "bank_name" not in rows[0]
    assert "closing_balance" not in rows[0]
    assert "base_currency" not in rows[0]
