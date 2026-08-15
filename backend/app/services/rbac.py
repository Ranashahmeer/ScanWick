from typing import Optional
from uuid import UUID

from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.user_merchant_roles import UserMerchantRole, Vertical
from app.schemas.envelope import error_response


async def get_merchant_role(
    db: AsyncSession, user_id: int, merchant_id: UUID, vertical: Vertical
) -> Optional[UserMerchantRole]:
    return (
        await db.execute(
            select(UserMerchantRole).where(
                UserMerchantRole.user_id == user_id,
                UserMerchantRole.merchant_id == merchant_id,
                UserMerchantRole.vertical == vertical,
            )
        )
    ).scalar_one_or_none()


async def check_role(
    db: AsyncSession,
    current_user: User,
    merchant_id: UUID,
    vertical: Vertical,
    allowed_roles: set[str],
) -> tuple[Optional[JSONResponse], Optional[UserMerchantRole]]:
    """Shared by every RBAC-protected ecommerce route. Returns
    (error_response_or_None, role_row) — same tuple-of-(error, ...)
    convention as `_parse_merchant_and_dates` (ecommerce.py) and the
    `require_merchant_role`/`require_account_role` dependencies
    (merchant_dependencies.py), not a raised HTTPException, so the 403 goes
    through the same standard envelope (`error_response`) every other error
    in this codebase uses.

    Two distinct 403 cases: the user has no role at all for this merchant/
    vertical (never granted access), vs. they have a role but it isn't
    permitted for this specific endpoint group."""
    role_row = await get_merchant_role(db, current_user.id, merchant_id, vertical)
    if role_row is None:
        return (
            JSONResponse(
                status_code=403,
                content=error_response(
                    "FORBIDDEN", f"You do not have access to this merchant's {vertical.value} data."
                ),
            ),
            None,
        )
    if role_row.role not in allowed_roles:
        return (
            JSONResponse(
                status_code=403,
                content=error_response(
                    "FORBIDDEN", f"Role '{role_row.role}' is not permitted to access this resource."
                ),
            ),
            None,
        )
    return None, role_row


async def check_any_role(
    db: AsyncSession, current_user: User, merchant_id: UUID, vertical: Vertical
) -> tuple[Optional[JSONResponse], Optional[UserMerchantRole]]:
    """Task 5.4: reconciliation-report reads must be reachable by every
    role with any read access at all, including roles this build doesn't
    have an exact name for ("Analyst," per the spec, with no defined
    access table anywhere in the repo — treated as covered by any granted
    role, since none of EcommerceRole/BankRole are write-only).
    Unlike `check_role()`, there's no `allowed_roles` set to check against
    — any role at all for this merchant/vertical is sufficient."""
    role_row = await get_merchant_role(db, current_user.id, merchant_id, vertical)
    if role_row is None:
        return (
            JSONResponse(
                status_code=403,
                content=error_response(
                    "FORBIDDEN", f"You do not have access to this merchant's {vertical.value} data."
                ),
            ),
            None,
        )
    return None, role_row


async def check_any_merchant_access(
    db: AsyncSession, current_user: User, merchant_id: UUID
) -> tuple[Optional[JSONResponse], Optional[UserMerchantRole]]:
    """Reports is the first genuinely cross-vertical feature — a single
    report can pull from bank/ecommerce data in one response, so
    gating it behind one specific `Vertical` (like `check_role`/
    `check_any_role` require) doesn't fit. Passes if the caller has ANY
    `UserMerchantRole` row for this merchant, in any vertical, any role —
    individual report generators are responsible for treating a vertical
    they can't actually reach as a disabled section, not for re-checking
    RBAC themselves."""
    role_row = (
        await db.execute(
            select(UserMerchantRole)
            .where(UserMerchantRole.user_id == current_user.id, UserMerchantRole.merchant_id == merchant_id)
            .order_by(UserMerchantRole.created_at)
            .limit(1)
        )
    ).scalar_one_or_none()
    if role_row is None:
        return (
            JSONResponse(
                status_code=403,
                content=error_response("FORBIDDEN", "You do not have access to this merchant."),
            ),
            None,
        )
    return None, role_row
