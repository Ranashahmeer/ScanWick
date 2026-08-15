import asyncio
import uuid

from sqlalchemy import select

from app.models import BankRole, EcommerceRole, UserMerchantRole, Vertical
from app.services.merchant_provisioning import ensure_merchant_provisioned


async def test_ensure_merchant_provisioned_creates_owner_role_on_both_verticals(db_session):
    merchant_id = await ensure_merchant_provisioned(db_session, user_id=7)

    roles = (
        (await db_session.execute(select(UserMerchantRole).where(UserMerchantRole.user_id == 7)))
        .scalars()
        .all()
    )
    by_vertical = {r.vertical: r for r in roles}

    assert len(roles) == 2
    assert all(r.merchant_id == merchant_id for r in roles)
    assert by_vertical[Vertical.ecommerce].role == EcommerceRole.owner.value
    assert by_vertical[Vertical.bank].role == BankRole.bank_owner.value


async def test_ensure_merchant_provisioned_is_idempotent(db_session):
    first_id = await ensure_merchant_provisioned(db_session, user_id=7)
    second_id = await ensure_merchant_provisioned(db_session, user_id=7)

    assert first_id == second_id
    roles = (
        (await db_session.execute(select(UserMerchantRole).where(UserMerchantRole.user_id == 7)))
        .scalars()
        .all()
    )
    assert len(roles) == 2


async def test_ensure_merchant_provisioned_is_per_user(db_session):
    merchant_id_a = await ensure_merchant_provisioned(db_session, user_id=1)
    merchant_id_b = await ensure_merchant_provisioned(db_session, user_id=2)

    assert merchant_id_a != merchant_id_b


async def test_ensure_merchant_provisioned_backfills_missing_verticals(db_session):
    """Found via live testing: an account seeded with a role for only one
    vertical (e.g. bank, from data that predates this provisioning step)
    must get the other backfilled — not be treated as "already done"
    just because some role row exists for the user."""
    existing_merchant_id = uuid.uuid4()
    db_session.add(
        UserMerchantRole(
            id=uuid.uuid4(),
            user_id=7,
            merchant_id=existing_merchant_id,
            vertical=Vertical.bank,
            role=BankRole.bank_owner.value,
        )
    )
    await db_session.commit()

    returned_id = await ensure_merchant_provisioned(db_session, user_id=7)

    assert returned_id == existing_merchant_id
    roles = (
        (await db_session.execute(select(UserMerchantRole).where(UserMerchantRole.user_id == 7)))
        .scalars()
        .all()
    )
    by_vertical = {r.vertical: r for r in roles}
    assert len(roles) == 2
    assert all(r.merchant_id == existing_merchant_id for r in roles)
    assert by_vertical[Vertical.bank].role == BankRole.bank_owner.value
    assert by_vertical[Vertical.ecommerce].role == EcommerceRole.owner.value


async def test_invited_role_is_never_backfilled_with_owner_access(db_session):
    """Regression test for the escalation bug found during the team-invite
    design: a user invited onto someone else's merchant with a single,
    narrow role (bank_viewer) must NOT get auto-promoted to owner of the
    other vertical the next time /me runs. Only roles seeded/created
    outside the invite flow (granted_via_invite=False, the default) are
    eligible for backfill."""
    other_business_merchant_id = uuid.uuid4()
    db_session.add(
        UserMerchantRole(
            id=uuid.uuid4(),
            user_id=7,
            merchant_id=other_business_merchant_id,
            vertical=Vertical.bank,
            role=BankRole.bank_viewer.value,
            granted_via_invite=True,
        )
    )
    await db_session.commit()

    returned_id = await ensure_merchant_provisioned(db_session, user_id=7)

    assert returned_id == other_business_merchant_id
    roles = (
        (await db_session.execute(select(UserMerchantRole).where(UserMerchantRole.user_id == 7)))
        .scalars()
        .all()
    )
    assert len(roles) == 1
    assert roles[0].role == BankRole.bank_viewer.value


async def test_concurrent_first_provisioning_uses_one_merchant_id(db_session_factory):
    async def provision_once():
        async with db_session_factory() as session:
            return await ensure_merchant_provisioned(session, user_id=7)

    first_id, second_id = await asyncio.gather(provision_once(), provision_once())

    async with db_session_factory() as session:
        roles = (
            (
                await session.execute(
                    select(UserMerchantRole).where(UserMerchantRole.user_id == 7)
                )
            )
            .scalars()
            .all()
        )

    assert first_id == second_id
    assert len(roles) == 2
    assert {role.merchant_id for role in roles} == {first_id}
    assert {role.vertical for role in roles} == set(Vertical)
