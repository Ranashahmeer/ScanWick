"""3.9: FastAPI dependencies that resolve and validate merchant/account
context BEFORE the route handler body runs.

This is a structural guarantee, not a call-ordering convention: FastAPI
resolves every `Depends()` before invoking the endpoint function, so
whatever these do can never run after business logic that a handler body
might otherwise put first. That mattered concretely in
`bank.py`'s `_load_account_and_transactions`, which used to load an
account, run a WRITE side-effect (the own-account-transfer scan), and load
every transaction before `check_role` was ever called back in the route
body -- an unauthenticated-for-this-merchant caller could trigger real
writes just by guessing an `account_id`.

Each dependency below returns a 3-tuple `(error, value, role_row)`:
`error` is a ready-to-return `JSONResponse` (or `None` on success) so a
route handler's very first line stays `if error is not None: return
error` -- unchanged from the existing convention elsewhere in these
routes, and no new exception-handling plumbing needed to keep the same
`error_response()` envelope shape.
"""
import uuid
from typing import Optional

from fastapi import Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.accounts import Account
from app.models.auth import User
from app.models.user_merchant_roles import UserMerchantRole, Vertical
from app.schemas.envelope import error_response
from app.services.rbac import check_role


def require_merchant_role(vertical: Vertical, allowed_roles: set[str]):
    """For routes where `merchant_id` is itself the query param (no lookup
    needed to know which merchant it names) -- ecommerce.py's dashboard/
    diagnostic routes, bank.py's `/accounts`. Validates the caller's role
    for that merchant/vertical before the handler body runs."""

    async def _dependency(
        merchant_id: str = Query(
            ..., description="RBAC is enforced by this dependency before any handler logic runs."
        ),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> tuple[Optional[JSONResponse], Optional[uuid.UUID], Optional[UserMerchantRole]]:
        try:
            merchant_uuid = uuid.UUID(merchant_id)
        except ValueError:
            return (
                JSONResponse(
                    status_code=400,
                    content=error_response("INVALID_MERCHANT_ID", f"'{merchant_id}' is not a valid UUID."),
                ),
                None,
                None,
            )
        error, role_row = await check_role(db, current_user, merchant_uuid, vertical, allowed_roles)
        if error is not None:
            return error, None, None
        return None, merchant_uuid, role_row

    return _dependency


def require_account_role(vertical: Vertical, allowed_roles: set[str]):
    """For bank.py's `account_id`-scoped routes, where resolving the owning
    merchant genuinely requires a lookup first (the account's `user_id` IS
    the merchant_id for the bank vertical -- see `UserMerchantRole`'s
    docstring). Loads ONLY the `Account` row -- no transactions, no
    transfer-detection scan -- so that minimal, side-effect-free read is
    the only thing that happens before authorization. The handler is
    responsible for loading transactions (and running the transfer scan)
    itself, afterwards, now that the caller is known to be authorized."""

    async def _dependency(
        account_id: str = Query(
            ..., description="RBAC is enforced by this dependency before any handler logic runs."
        ),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> tuple[Optional[JSONResponse], Optional[Account], Optional[UserMerchantRole]]:
        try:
            account_uuid = uuid.UUID(account_id)
        except ValueError:
            return (
                JSONResponse(
                    status_code=400,
                    content=error_response("INVALID_ACCOUNT_ID", f"'{account_id}' is not a valid UUID."),
                ),
                None,
                None,
            )
        account = (await db.execute(select(Account).where(Account.id == account_uuid))).scalar_one_or_none()
        if account is None:
            return (
                JSONResponse(
                    status_code=404,
                    content=error_response("ACCOUNT_NOT_FOUND", f"No account found for account_id {account_id}."),
                ),
                None,
                None,
            )
        error, role_row = await check_role(db, current_user, account.user_id, vertical, allowed_roles)
        if error is not None:
            return error, None, None
        return None, account, role_row

    return _dependency
