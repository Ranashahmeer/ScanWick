import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BankRole, EcommerceRole, UserMerchantRole, Vertical


_OWNER_ROLE_BY_VERTICAL = {
    Vertical.ecommerce: EcommerceRole.owner.value,
    Vertical.bank: BankRole.bank_owner.value,
}
_AUTO_MERCHANT_NAMESPACE = uuid.UUID("0d3bd8a8-2cdb-44c2-8f85-0d4e8d6b5f66")


async def ensure_merchant_provisioned(db: AsyncSession, user_id: int) -> uuid.UUID:
    """Every upload/dashboard route requires a merchant_id plus a
    UserMerchantRole row to pass RBAC — neither registration nor Google
    login ever created one, so every new account was permanently locked out
    of both verticals with no way to self-serve in. Auto-provisions a
    merchant_id (one user = one merchant, owner-tier role on both
    verticals) the first time this runs for a user. Idempotent — safe to
    call on every login/me fetch, not just once at signup.

    Backfills per-vertical, not all-or-nothing: found via live testing that
    an account with a role for only one vertical (e.g. a pre-existing bank
    role seeded before this provisioning step existed) got permanently
    stuck without ecommerce access — the original version bailed out
    the moment it found *any* role row for the user, never checking whether
    the other vertical was covered.
    """
    existing_roles = await _fetch_user_roles(db, user_id)

    if not existing_roles:
        merchant_id = _auto_merchant_id_for_user(user_id)
        covered = set()
        same_merchant_roles: list[UserMerchantRole] = []
    else:
        merchant_id = existing_roles[0].merchant_id
        same_merchant_roles = [role for role in existing_roles if role.merchant_id == merchant_id]
        covered = {role.vertical for role in same_merchant_roles}

    # Self-provisioning (auto-granting owner-tier roles for missing verticals)
    # must never touch a merchant the user was invited into — only a merchant
    # they own outright. `granted_via_invite` distinguishes the two: a role
    # created by team_management.accept_invite() is always for someone
    # ELSE's business, and treating its "missing verticals" as needing an
    # owner-tier backfill would silently escalate an invited viewer/rep into
    # owning every vertical their inviter never granted them. Legacy/seeded
    # roles (granted_via_invite defaults False) keep backfilling exactly as
    # before — this only changes behavior for genuinely new, invited roles.
    if any(role.granted_via_invite for role in same_merchant_roles):
        return merchant_id

    missing = [vertical for vertical in Vertical if vertical not in covered]
    if not missing:
        return merchant_id

    try:
        for vertical in missing:
            db.add(
                UserMerchantRole(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    merchant_id=merchant_id,
                    vertical=vertical,
                    role=_OWNER_ROLE_BY_VERTICAL[vertical],
                )
            )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing_roles = await _fetch_user_roles(db, user_id)
        if existing_roles:
            return existing_roles[0].merchant_id
        raise

    return merchant_id


async def _fetch_user_roles(db: AsyncSession, user_id: int) -> list[UserMerchantRole]:
    return (
        (
            await db.execute(
                select(UserMerchantRole)
                .where(UserMerchantRole.user_id == user_id)
                .order_by(UserMerchantRole.created_at, UserMerchantRole.id)
            )
        )
        .scalars()
        .all()
    )


def _auto_merchant_id_for_user(user_id: int) -> uuid.UUID:
    return uuid.uuid5(_AUTO_MERCHANT_NAMESPACE, str(user_id))


def is_primary_owner(user_id: int, merchant_id: uuid.UUID) -> bool:
    """True only for the one user whose own auto-derived merchant this is —
    i.e. the person `ensure_merchant_provisioned` originally self-provisioned
    as owner of both verticals, as opposed to someone later invited onto
    this merchant with a specific, narrower role. This is the single
    permission gate for team management (invite/edit/remove teammates):
    one business, one primary owner account, matching how merchant identity
    already works everywhere else in this module."""
    return merchant_id == _auto_merchant_id_for_user(user_id)
