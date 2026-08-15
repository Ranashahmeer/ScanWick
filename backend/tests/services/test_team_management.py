import pytest
from sqlalchemy import select

from app.models import User, UserMerchantRole, Vertical
from app.services import team_management
from app.services.merchant_provisioning import ensure_merchant_provisioned


async def _make_owner(db_session, *, id: int, email: str) -> User:
    user = User(id=id, email=email, first_name="Owner", last_name="One", is_verified=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    await ensure_merchant_provisioned(db_session, user.id)
    return user


async def test_create_invite_requires_primary_owner(db_session):
    owner = await _make_owner(db_session, id=1, email="owner@example.com")
    non_owner = User(id=2, email="not-the-owner@example.com", is_verified=True)
    db_session.add(non_owner)
    await db_session.commit()

    merchant_id = await ensure_merchant_provisioned(db_session, owner.id)

    with pytest.raises(PermissionError):
        await team_management.create_invite(
            db_session, non_owner, merchant_id, email="new@example.com", vertical=Vertical.bank, role="bank_viewer"
        )


async def test_create_invite_rejects_invalid_role(db_session):
    owner = await _make_owner(db_session, id=1, email="owner@example.com")
    merchant_id = await ensure_merchant_provisioned(db_session, owner.id)

    with pytest.raises(ValueError):
        await team_management.create_invite(
            db_session, owner, merchant_id, email="new@example.com", vertical=Vertical.bank, role="not_a_real_role"
        )


async def test_accept_invite_new_account_creates_user_and_grants_only_the_invited_role(db_session):
    owner = await _make_owner(db_session, id=1, email="owner@example.com")
    merchant_id = await ensure_merchant_provisioned(db_session, owner.id)

    invite = await team_management.create_invite(
        db_session, owner, merchant_id, email="teammate@example.com", vertical=Vertical.bank, role="bank_viewer"
    )

    user, tokens = await team_management.accept_invite(
        db_session, invite.token, first_name="Tee", last_name="Mate", password="a-strong-password"
    )

    assert user.email == "teammate@example.com"
    assert user.is_verified is True
    assert tokens is not None  # logged in immediately, same as any other new session

    roles = (
        (await db_session.execute(select(UserMerchantRole).where(UserMerchantRole.user_id == user.id)))
        .scalars()
        .all()
    )
    assert len(roles) == 1
    assert roles[0].merchant_id == merchant_id
    assert roles[0].vertical == Vertical.bank
    assert roles[0].role == "bank_viewer"
    assert roles[0].granted_via_invite is True

    # The invited user's OWN /me-equivalent provisioning must never escalate
    # them to owner of the other vertical on the inviter's merchant — the
    # B1 fix this feature required (also regression-tested directly in
    # test_merchant_provisioning.py).
    resolved_merchant_id = await ensure_merchant_provisioned(db_session, user.id)
    assert resolved_merchant_id == merchant_id
    roles_after = (
        (await db_session.execute(select(UserMerchantRole).where(UserMerchantRole.user_id == user.id)))
        .scalars()
        .all()
    )
    assert len(roles_after) == 1


async def test_accept_invite_existing_account_requires_matching_login(db_session):
    owner = await _make_owner(db_session, id=1, email="owner@example.com")
    merchant_id = await ensure_merchant_provisioned(db_session, owner.id)

    existing_teammate = User(id=3, email="teammate@example.com", is_verified=True)
    db_session.add(existing_teammate)
    await db_session.commit()

    invite = await team_management.create_invite(
        db_session, owner, merchant_id, email="teammate@example.com", vertical=Vertical.ecommerce, role="viewer"
    )

    wrong_user = User(id=4, email="someone-else@example.com", is_verified=True)
    db_session.add(wrong_user)
    await db_session.commit()

    with pytest.raises(PermissionError):
        await team_management.accept_invite(db_session, invite.token, accepting_user=wrong_user)

    user, tokens = await team_management.accept_invite(db_session, invite.token, accepting_user=existing_teammate)
    assert user.id == existing_teammate.id
    assert tokens is None  # already logged in — no new session needed


async def test_revoked_invite_cannot_be_accepted(db_session):
    owner = await _make_owner(db_session, id=1, email="owner@example.com")
    merchant_id = await ensure_merchant_provisioned(db_session, owner.id)
    invite = await team_management.create_invite(
        db_session, owner, merchant_id, email="teammate@example.com", vertical=Vertical.bank, role="bank_viewer"
    )

    await team_management.revoke_invite(db_session, owner, merchant_id, invite.id)

    with pytest.raises(ValueError):
        await team_management.accept_invite(
            db_session, invite.token, first_name="Tee", last_name="Mate", password="a-strong-password"
        )


async def test_remove_member_blocks_self_removal(db_session):
    owner = await _make_owner(db_session, id=1, email="owner@example.com")
    merchant_id = await ensure_merchant_provisioned(db_session, owner.id)

    with pytest.raises(ValueError):
        await team_management.remove_member(db_session, owner, merchant_id, owner.id)


async def test_update_member_role_blocks_self_edit(db_session):
    owner = await _make_owner(db_session, id=1, email="owner@example.com")
    merchant_id = await ensure_merchant_provisioned(db_session, owner.id)

    with pytest.raises(ValueError):
        await team_management.update_member_role(
            db_session, owner, merchant_id, owner.id, vertical=Vertical.bank, role="bank_admin"
        )


async def test_list_members_includes_owner_and_invited_teammate(db_session):
    owner = await _make_owner(db_session, id=1, email="owner@example.com")
    merchant_id = await ensure_merchant_provisioned(db_session, owner.id)
    invite = await team_management.create_invite(
        db_session, owner, merchant_id, email="teammate@example.com", vertical=Vertical.bank, role="bank_viewer"
    )
    await team_management.accept_invite(
        db_session, invite.token, first_name="Tee", last_name="Mate", password="a-strong-password"
    )

    members = await team_management.list_members(db_session, merchant_id)
    emails = {member["email"] for member in members}
    assert "owner@example.com" in emails
    assert "teammate@example.com" in emails
