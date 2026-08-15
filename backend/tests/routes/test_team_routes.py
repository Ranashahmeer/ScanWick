def test_get_members_returns_the_solo_owners_own_two_roles(authenticated_client, db_session_factory, test_user):
    import asyncio

    from app.models import User

    async def _seed_user() -> None:
        async with db_session_factory() as session:
            session.add(User(id=test_user.id, email=test_user.email, is_verified=True))
            await session.commit()

    # list_members joins UserMerchantRole against a real `users` row —
    # authenticated_client's dependency-override user only exists in-memory,
    # so a real row with the same id/email is seeded here to match what
    # get_current_user would return for an actually-authenticated request.
    asyncio.run(_seed_user())

    response = authenticated_client.get("/api/v1/team/members")

    assert response.status_code == 200
    body = response.json()["data"]
    # A brand-new user is auto-provisioned as owner of both verticals
    # on their own merchant (merchant_provisioning.ensure_merchant_provisioned)
    # — that's what a solo owner's team list looks like before inviting anyone.
    assert len(body["members"]) == 2
    assert body["pending_invites"] == []


def test_get_my_businesses_returns_the_solo_owners_own_business(authenticated_client, test_user):
    """3.9: discovery endpoint for the active-business context -- a
    brand-new user sees exactly their own auto-provisioned business, marked
    `is_own_business`, with owner-tier roles on both verticals."""
    response = authenticated_client.get("/api/v1/team/my-businesses")

    assert response.status_code == 200
    businesses = response.json()["data"]["businesses"]
    assert len(businesses) == 1
    assert businesses[0]["is_own_business"] is True
    assert businesses[0]["roles"] == {
        "ecommerce": "owner",
        "bank": "bank_owner",
    }


def test_get_my_businesses_includes_a_business_the_user_was_invited_into(
    authenticated_client, db_session_factory, test_user
):
    """A user who belongs to more than one business (their own, plus one
    they were invited into) must see both here -- the whole point of this
    endpoint, since that's the "legitimately belong to multiple businesses"
    case the active-business context exists for."""
    import asyncio
    import uuid

    from app.models import UserMerchantRole, Vertical
    from app.services.merchant_provisioning import ensure_merchant_provisioned

    invited_merchant_id = uuid.uuid4()

    async def _provision_own_business_then_seed_invited_role() -> None:
        async with db_session_factory() as session:
            # Realistic ordering: a user's own business is always provisioned
            # first (at register/login, see auth.py) -- an invite always
            # comes after. `ensure_merchant_provisioned` treats the FIRST
            # role a user ever has as "their own merchant"; seeding the
            # invited role before this step would (correctly) make IT look
            # like the user's own business instead.
            await ensure_merchant_provisioned(session, test_user.id)
            session.add(
                UserMerchantRole(
                    id=uuid.uuid4(),
                    user_id=test_user.id,
                    merchant_id=invited_merchant_id,
                    vertical=Vertical.bank,
                    role="loan_officer",
                    granted_via_invite=True,
                )
            )
            await session.commit()

    asyncio.run(_provision_own_business_then_seed_invited_role())

    response = authenticated_client.get("/api/v1/team/my-businesses")

    assert response.status_code == 200
    businesses = {b["merchant_id"]: b for b in response.json()["data"]["businesses"]}
    assert len(businesses) == 2
    invited = businesses[str(invited_merchant_id)]
    assert invited["is_own_business"] is False
    assert invited["roles"] == {"bank": "loan_officer"}
    own = [b for b in businesses.values() if b["merchant_id"] != str(invited_merchant_id)][0]
    assert own["is_own_business"] is True


def test_invite_then_list_shows_a_pending_invite(authenticated_client):
    invite_response = authenticated_client.post(
        "/api/v1/team/invite",
        json={"email": "teammate@example.com", "vertical": "bank", "role": "bank_viewer"},
    )
    assert invite_response.status_code == 200
    assert invite_response.json()["data"]["email"] == "teammate@example.com"

    members_response = authenticated_client.get("/api/v1/team/members")
    pending = members_response.json()["data"]["pending_invites"]
    assert len(pending) == 1
    assert pending[0]["status"] == "pending"


def test_invite_rejects_self(authenticated_client):
    response = authenticated_client.post(
        "/api/v1/team/invite",
        json={"email": "fixture-user@example.com", "vertical": "bank", "role": "bank_viewer"},
    )
    assert response.status_code == 422


def test_invite_rejects_invalid_role(authenticated_client):
    response = authenticated_client.post(
        "/api/v1/team/invite",
        json={"email": "teammate@example.com", "vertical": "bank", "role": "not_a_real_role"},
    )
    assert response.status_code == 422


def test_remove_self_is_rejected(authenticated_client, test_user):
    response = authenticated_client.delete(f"/api/v1/team/members/{test_user.id}")
    assert response.status_code == 422
