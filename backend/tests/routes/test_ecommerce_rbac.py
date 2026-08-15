"""RBAC tests for Ecommerce (task 5.1) — real `UserMerchantRole` rows,
real enforcement, no bypass. Uses `rbac_client`/`as_user()` from
conftest.py, not the `client` fixture (which bypasses RBAC for the
existing, pre-5.1 functional test suite)."""

import uuid

from app.models.user_merchant_roles import EcommerceRole, UserMerchantRole, Vertical
from app.models.auth import User
from tests.conftest import as_user


def _make_user(user_id: int) -> User:
    # premium: this suite tests RBAC (role), not plan-tier gating — see
    # test_ecommerce_plan_gating.py for the latter.
    return User(
        id=user_id, email=f"user{user_id}@example.com", first_name="Test", last_name="User", is_verified=True,
        subscription_tier="premium",
    )


async def _grant_role(db_session, user_id: int, merchant_id, role: str) -> None:
    db_session.add(
        UserMerchantRole(id=uuid.uuid4(), user_id=user_id, merchant_id=merchant_id, vertical=Vertical.ecommerce, role=role)
    )
    await db_session.commit()


# ── READ group: dashboard/diagnostic/predictive/ai — all four roles allowed ──


async def test_owner_can_read(rbac_client, db_session):
    merchant_id = uuid.uuid4()
    user = _make_user(1)
    await _grant_role(db_session, user.id, merchant_id, EcommerceRole.owner.value)
    as_user(user)

    response = await rbac_client.get(f"/api/v1/ecommerce/dashboard/summary?merchant_id={merchant_id}")
    assert response.status_code == 200


async def test_admin_can_read(rbac_client, db_session):
    merchant_id = uuid.uuid4()
    user = _make_user(2)
    await _grant_role(db_session, user.id, merchant_id, EcommerceRole.admin.value)
    as_user(user)

    response = await rbac_client.get(f"/api/v1/ecommerce/dashboard/summary?merchant_id={merchant_id}")
    assert response.status_code == 200


async def test_manager_can_read(rbac_client, db_session):
    merchant_id = uuid.uuid4()
    user = _make_user(3)
    await _grant_role(db_session, user.id, merchant_id, EcommerceRole.manager.value)
    as_user(user)

    response = await rbac_client.get(f"/api/v1/ecommerce/dashboard/summary?merchant_id={merchant_id}")
    assert response.status_code == 200


async def test_viewer_can_read(rbac_client, db_session):
    merchant_id = uuid.uuid4()
    user = _make_user(4)
    await _grant_role(db_session, user.id, merchant_id, EcommerceRole.viewer.value)
    as_user(user)

    response = await rbac_client.get(f"/api/v1/ecommerce/dashboard/summary?merchant_id={merchant_id}")
    assert response.status_code == 200


# ── No role at all for this merchant: the other 403 branch in check_role ──


async def test_user_with_no_role_for_merchant_is_denied(rbac_client, db_session):
    merchant_id = uuid.uuid4()
    user = _make_user(13)
    as_user(user)  # no UserMerchantRole row granted at all

    response = await rbac_client.get(f"/api/v1/ecommerce/dashboard/summary?merchant_id={merchant_id}")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_role_granted_for_a_different_merchant_does_not_grant_this_one(rbac_client, db_session):
    """A role row exists, but for a different merchant_id -- must not
    leak access to an unrelated merchant."""
    granted_merchant_id = uuid.uuid4()
    requested_merchant_id = uuid.uuid4()
    user = _make_user(14)
    await _grant_role(db_session, user.id, granted_merchant_id, EcommerceRole.owner.value)
    as_user(user)

    response = await rbac_client.get(f"/api/v1/ecommerce/dashboard/summary?merchant_id={requested_merchant_id}")
    assert response.status_code == 403
