from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, get_current_user_optional
from app.models import User, UserMerchantRole, Vertical
from app.schemas.envelope import error_response, success_response
from app.services import team_management
from app.services.merchant_provisioning import ensure_merchant_provisioned

router = APIRouter(prefix="/api/v1/team", tags=["team"])


def _serialize_invite(invite) -> dict:
    return {
        "id": str(invite.id),
        "email": invite.email,
        "vertical": invite.vertical.value,
        "role": invite.role,
        "rep_id": str(invite.rep_id) if invite.rep_id else None,
        "status": invite.status.value,
        "expires_at": invite.expires_at.isoformat() if invite.expires_at else None,
    }


class InviteRequest(BaseModel):
    email: str
    vertical: Vertical
    role: str
    rep_id: Optional[UUID] = None


class UpdateMemberRoleRequest(BaseModel):
    vertical: Vertical
    role: str
    rep_id: Optional[UUID] = None


class AcceptInviteRequest(BaseModel):
    # Only required when the invited email has no existing account yet —
    # see team_management.accept_invite.
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = None


@router.get("/members")
async def get_members(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    merchant_id = await ensure_merchant_provisioned(db, current_user.id)
    if not team_management.is_primary_owner(current_user.id, merchant_id):
        return JSONResponse(
            status_code=403, content=error_response("FORBIDDEN", "Only this team's primary owner can view it.")
        )
    members = await team_management.list_members(db, merchant_id)
    invites = await team_management.list_pending_invites(db, merchant_id)
    return success_response({"members": members, "pending_invites": [_serialize_invite(i) for i in invites]})


@router.get("/my-businesses")
async def get_my_businesses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """3.9: an explicit active-business discovery endpoint for users who
    legitimately belong to multiple businesses (their own self-provisioned
    one, plus any they've been invited into) -- lets the frontend present a
    switcher, rather than the caller needing to already know which
    merchant_id to pass on every dashboard/diagnostic request. Every other
    route in this app still takes merchant_id as an explicit, RBAC-
    validated parameter (see `require_merchant_role`/`require_account_role`
    in `merchant_dependencies.py`); this endpoint is what a client uses to
    discover which merchant_id values it's even allowed to pass.

    Ensures the caller's own merchant is provisioned first (same as every
    other team.py route) so a brand-new user always sees at least their own
    business here, even before their first upload."""
    await ensure_merchant_provisioned(db, current_user.id)
    rows = (
        (
            await db.execute(
                select(UserMerchantRole)
                .where(UserMerchantRole.user_id == current_user.id)
                .order_by(UserMerchantRole.created_at)
            )
        )
        .scalars()
        .all()
    )

    businesses: dict[UUID, dict] = {}
    for row in rows:
        entry = businesses.setdefault(
            row.merchant_id,
            {
                "merchant_id": str(row.merchant_id),
                "is_own_business": team_management.is_primary_owner(current_user.id, row.merchant_id),
                "roles": {},
            },
        )
        entry["roles"][row.vertical.value] = row.role

    return success_response({"businesses": list(businesses.values())})


@router.post("/invite")
async def invite_member(
    body: InviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    merchant_id = await ensure_merchant_provisioned(db, current_user.id)
    try:
        invite = await team_management.create_invite(
            db, current_user, merchant_id, email=body.email, vertical=body.vertical, role=body.role, rep_id=body.rep_id
        )
    except PermissionError as exc:
        return JSONResponse(status_code=403, content=error_response("FORBIDDEN", str(exc)))
    except ValueError as exc:
        return JSONResponse(status_code=422, content=error_response("INVALID_INVITE", str(exc)))
    return success_response(_serialize_invite(invite))


@router.post("/invite/{invite_id}/resend")
async def resend_invite(
    invite_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    merchant_id = await ensure_merchant_provisioned(db, current_user.id)
    try:
        invite = await team_management.resend_invite(db, current_user, merchant_id, invite_id)
    except PermissionError as exc:
        return JSONResponse(status_code=403, content=error_response("FORBIDDEN", str(exc)))
    except ValueError as exc:
        return JSONResponse(status_code=404, content=error_response("INVITE_NOT_FOUND", str(exc)))
    return success_response(_serialize_invite(invite))


@router.delete("/invite/{invite_id}")
async def revoke_invite(
    invite_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    merchant_id = await ensure_merchant_provisioned(db, current_user.id)
    try:
        await team_management.revoke_invite(db, current_user, merchant_id, invite_id)
    except PermissionError as exc:
        return JSONResponse(status_code=403, content=error_response("FORBIDDEN", str(exc)))
    except ValueError as exc:
        return JSONResponse(status_code=404, content=error_response("INVITE_NOT_FOUND", str(exc)))
    return success_response({"revoked": True})


@router.post("/invite/{token}/accept")
async def accept_invite(
    token: str,
    body: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """No owner check — the token itself is the credential. Uses
    `get_current_user_optional` rather than `get_current_user`: the
    new-account path has no session yet (an Authorization header simply
    won't be present), while the existing-account path requires one, which
    `team_management.accept_invite` itself enforces by checking
    `accepting_user.email == invite.email`."""
    try:
        user, tokens = await team_management.accept_invite(
            db,
            token,
            accepting_user=current_user,
            first_name=body.first_name,
            last_name=body.last_name,
            password=body.password,
        )
    except PermissionError as exc:
        return JSONResponse(status_code=403, content=error_response("FORBIDDEN", str(exc)))
    except ValueError as exc:
        return JSONResponse(status_code=422, content=error_response("INVALID_INVITE", str(exc)))

    return success_response(
        {
            "user": {"id": user.id, "email": user.email},
            "tokens": tokens.model_dump() if tokens else None,
        }
    )


@router.patch("/members/{target_user_id}")
async def update_member(
    target_user_id: int,
    body: UpdateMemberRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    merchant_id = await ensure_merchant_provisioned(db, current_user.id)
    try:
        row = await team_management.update_member_role(
            db, current_user, merchant_id, target_user_id, vertical=body.vertical, role=body.role, rep_id=body.rep_id
        )
    except PermissionError as exc:
        return JSONResponse(status_code=403, content=error_response("FORBIDDEN", str(exc)))
    except ValueError as exc:
        return JSONResponse(status_code=422, content=error_response("INVALID_ROLE_UPDATE", str(exc)))
    return success_response({"user_id": row.user_id, "vertical": row.vertical.value, "role": row.role})


@router.delete("/members/{target_user_id}")
async def delete_member(
    target_user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    merchant_id = await ensure_merchant_provisioned(db, current_user.id)
    try:
        await team_management.remove_member(db, current_user, merchant_id, target_user_id)
    except PermissionError as exc:
        return JSONResponse(status_code=403, content=error_response("FORBIDDEN", str(exc)))
    except ValueError as exc:
        return JSONResponse(status_code=422, content=error_response("INVALID_REMOVAL", str(exc)))
    return success_response({"removed": True})
