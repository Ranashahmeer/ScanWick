"""Invite-a-teammate + role-management business logic. Only the merchant's
primary owner (`merchant_provisioning.is_primary_owner`) may view, invite,
edit, or remove teammates — see that function's docstring for why "primary
owner" is the one permission gate rather than any per-vertical owner role.

Raises plain `ValueError`/`PermissionError` on invalid input or unauthorized
access; `app.routes.team` translates those into the standard error envelope.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from typing import Optional
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import (
    BankRole,
    EcommerceRole,
    RefreshToken,
    TeamInvite,
    TeamInviteStatus,
    User,
    UserMerchantRole,
    Vertical,
)
from app.schemas import TokenResponse
from app.services.merchant_provisioning import is_primary_owner
from app.utils.email import send_team_invite_email
from app.utils.security import create_access_token, create_refresh_token_str, hash_password, refresh_token_expiry

_INVITE_TOKEN_TTL = timedelta(days=7)

_ROLE_ENUM_BY_VERTICAL = {
    Vertical.ecommerce: EcommerceRole,
    Vertical.bank: BankRole,
}


def _validate_role(vertical: Vertical, role: str, rep_id: Optional[UUID]) -> None:
    valid_roles = {member.value for member in _ROLE_ENUM_BY_VERTICAL[vertical]}
    if role not in valid_roles:
        raise ValueError(
            f"'{role}' is not a valid role for vertical '{vertical.value}'. "
            f"Must be one of: {', '.join(sorted(valid_roles))}."
        )


async def _issue_tokens(db: AsyncSession, user: User) -> TokenResponse:
    """Same shape as routes/auth.py's private `_issue_tokens` — duplicated
    rather than imported across route/service boundaries, since that helper
    is private to the auth route module."""
    access_token = create_access_token(user.id, user.email)
    raw_refresh = create_refresh_token_str()
    db.add(RefreshToken(user_id=user.id, token=raw_refresh, expires_at=refresh_token_expiry()))
    await db.commit()
    return TokenResponse(access_token=access_token, refresh_token=raw_refresh)


def _require_primary_owner(user_id: int, merchant_id: UUID) -> None:
    if not is_primary_owner(user_id, merchant_id):
        raise PermissionError("Only the primary owner of this merchant can manage its team.")


# ── Members ──────────────────────────────────────────────────────────────────

async def list_members(db: AsyncSession, merchant_id: UUID) -> list[dict]:
    rows = (
        await db.execute(
            select(UserMerchantRole, User)
            .join(User, User.id == UserMerchantRole.user_id)
            .where(UserMerchantRole.merchant_id == merchant_id)
            .order_by(User.email, UserMerchantRole.vertical)
        )
    ).all()
    return [
        {
            "user_id": role.user_id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "vertical": role.vertical.value,
            "role": role.role,
            "rep_id": str(role.rep_id) if role.rep_id else None,
        }
        for role, user in rows
    ]


async def update_member_role(
    db: AsyncSession,
    inviter: User,
    merchant_id: UUID,
    target_user_id: int,
    *,
    vertical: Vertical,
    role: str,
    rep_id: Optional[UUID] = None,
) -> UserMerchantRole:
    _require_primary_owner(inviter.id, merchant_id)
    if target_user_id == inviter.id:
        raise ValueError("You can't change your own role — you're this merchant's primary owner.")
    _validate_role(vertical, role, rep_id)

    row = (
        await db.execute(
            select(UserMerchantRole).where(
                UserMerchantRole.merchant_id == merchant_id,
                UserMerchantRole.user_id == target_user_id,
                UserMerchantRole.vertical == vertical,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise ValueError("This user has no role for that vertical on your team.")

    row.role = role
    row.rep_id = rep_id
    await db.commit()
    return row


async def remove_member(db: AsyncSession, inviter: User, merchant_id: UUID, target_user_id: int) -> None:
    _require_primary_owner(inviter.id, merchant_id)
    if target_user_id == inviter.id:
        raise ValueError("You can't remove yourself — you're this merchant's primary owner.")

    await db.execute(
        delete(UserMerchantRole).where(
            UserMerchantRole.merchant_id == merchant_id, UserMerchantRole.user_id == target_user_id
        )
    )
    await db.commit()


# ── Invites ──────────────────────────────────────────────────────────────────

async def list_pending_invites(db: AsyncSession, merchant_id: UUID) -> list[TeamInvite]:
    return (
        (
            await db.execute(
                select(TeamInvite)
                .where(TeamInvite.merchant_id == merchant_id, TeamInvite.status == TeamInviteStatus.pending)
                .order_by(TeamInvite.created_at.desc())
            )
        )
        .scalars()
        .all()
    )


async def create_invite(
    db: AsyncSession,
    inviter: User,
    merchant_id: UUID,
    *,
    email: str,
    vertical: Vertical,
    role: str,
    rep_id: Optional[UUID] = None,
) -> TeamInvite:
    _require_primary_owner(inviter.id, merchant_id)
    if email.lower() == inviter.email.lower():
        raise ValueError("You can't invite yourself.")
    _validate_role(vertical, role, rep_id)

    existing = (
        await db.execute(
            select(TeamInvite).where(
                TeamInvite.merchant_id == merchant_id,
                TeamInvite.email == email,
                TeamInvite.vertical == vertical,
                TeamInvite.status == TeamInviteStatus.pending,
            )
        )
    ).scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if existing is not None:
        # Re-inviting to the same vertical while a pending invite already
        # exists refreshes it in place rather than creating a duplicate row.
        invite = existing
        invite.role = role
        invite.rep_id = rep_id
    else:
        invite = TeamInvite(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            invited_by_user_id=inviter.id,
            email=email,
            vertical=vertical,
            role=role,
            rep_id=rep_id,
            status=TeamInviteStatus.pending,
        )
        db.add(invite)

    invite.token = token_urlsafe(32)
    invite.expires_at = now + _INVITE_TOKEN_TTL
    await db.commit()
    await db.refresh(invite)

    accept_link = f"{settings.frontend_url}/accept-invite?token={invite.token}"
    await send_team_invite_email(email, inviter.first_name or inviter.email, accept_link)
    return invite


async def resend_invite(db: AsyncSession, inviter: User, merchant_id: UUID, invite_id: UUID) -> TeamInvite:
    _require_primary_owner(inviter.id, merchant_id)
    invite = (
        await db.execute(
            select(TeamInvite).where(TeamInvite.id == invite_id, TeamInvite.merchant_id == merchant_id)
        )
    ).scalar_one_or_none()
    if invite is None or invite.status != TeamInviteStatus.pending:
        raise ValueError("No pending invite found with that id.")

    invite.token = token_urlsafe(32)
    invite.expires_at = datetime.now(timezone.utc) + _INVITE_TOKEN_TTL
    await db.commit()

    accept_link = f"{settings.frontend_url}/accept-invite?token={invite.token}"
    await send_team_invite_email(invite.email, inviter.first_name or inviter.email, accept_link)
    return invite


async def revoke_invite(db: AsyncSession, inviter: User, merchant_id: UUID, invite_id: UUID) -> None:
    _require_primary_owner(inviter.id, merchant_id)
    invite = (
        await db.execute(
            select(TeamInvite).where(TeamInvite.id == invite_id, TeamInvite.merchant_id == merchant_id)
        )
    ).scalar_one_or_none()
    if invite is None:
        raise ValueError("No invite found with that id.")

    invite.status = TeamInviteStatus.revoked
    await db.commit()


async def accept_invite(
    db: AsyncSession,
    token: str,
    *,
    accepting_user: Optional[User] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    password: Optional[str] = None,
) -> tuple[User, Optional[TokenResponse]]:
    """Two paths, both ending with a `granted_via_invite=True` role row for
    the inviter's merchant — never a full self-provisioned merchant of the
    invitee's own (see the `ensure_merchant_provisioned` fix this feature
    required):

    - No account exists yet for the invited email: `first_name`/`last_name`/
      `password` are required, a new verified `User` is created (the invite
      link itself is the proof of email ownership — same trust level as a
      password-reset link), and fresh tokens are returned so they land
      logged in.
    - An account already exists: `accepting_user` must already be
      authenticated as that exact email (log in first, then accept) — no
      new tokens are returned since they're already logged in.
    """
    invite = (await db.execute(select(TeamInvite).where(TeamInvite.token == token))).scalar_one_or_none()
    if invite is None:
        raise ValueError("This invite link is invalid.")
    if invite.status != TeamInviteStatus.pending:
        raise ValueError("This invite has already been used, revoked, or expired.")
    if invite.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        invite.status = TeamInviteStatus.expired
        await db.commit()
        raise ValueError("This invite link has expired. Ask whoever invited you to resend it.")

    existing_user = (await db.execute(select(User).where(User.email == invite.email))).scalar_one_or_none()
    tokens: Optional[TokenResponse] = None

    if existing_user is None:
        if not (first_name and last_name and password):
            raise ValueError("first_name, last_name, and password are required to accept this invite.")
        user = User(
            first_name=first_name,
            last_name=last_name,
            email=invite.email,
            hashed_password=hash_password(password),
            is_verified=True,
        )
        db.add(user)
        await db.flush()  # populates user.id (autoincrement PK), needed below
        tokens = await _issue_tokens(db, user)
    else:
        if accepting_user is None or accepting_user.email.lower() != invite.email.lower():
            raise PermissionError("Log in as the invited email address first, then accept this invite.")
        user = existing_user

    db.add(
        UserMerchantRole(
            id=uuid.uuid4(),
            user_id=user.id,
            merchant_id=invite.merchant_id,
            vertical=invite.vertical,
            role=invite.role,
            rep_id=invite.rep_id,
            granted_via_invite=True,
        )
    )
    invite.status = TeamInviteStatus.accepted
    await db.commit()

    return user, tokens
