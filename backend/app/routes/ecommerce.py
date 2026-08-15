from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.auth import User
from app.models.user_merchant_roles import EcommerceRole, Vertical
from app.schemas.envelope import error_response, success_response
from app.services.ecommerce_dashboard import compute_dashboard_summary
from app.services.ecommerce_revenue import compute_dashboard_revenue
from app.services.entitlements import check_feature_access
from app.services.merchant_dependencies import require_merchant_role

# Access table (RBAC — E-commerce, task 5.1): all four roles can read the
# surviving dashboard/summary and dashboard/revenue endpoints.
READ_ROLES = {
    EcommerceRole.owner.value,
    EcommerceRole.admin.value,
    EcommerceRole.manager.value,
    EcommerceRole.viewer.value,
}


router = APIRouter(prefix="/api/v1/ecommerce", tags=["ecommerce"])


def _parse_dates(date_from: str | None, date_to: str | None):
    """Shared by dashboard/summary and dashboard/revenue. merchant_id is
    already resolved+validated by the `require_merchant_role` dependency
    (3.9) rather than parsed here. Returns (error_response_or_None,
    parsed_from, parsed_to)."""
    try:
        parsed_from = date.fromisoformat(date_from) if date_from else None
        parsed_to = date.fromisoformat(date_to) if date_to else None
    except ValueError:
        return (
            JSONResponse(
                status_code=400,
                content=error_response("INVALID_DATE", "date_from/date_to must be ISO dates (YYYY-MM-DD)."),
            ),
            None,
            None,
        )
    return None, parsed_from, parsed_to


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    # 3.9: RBAC is resolved as a dependency (`require_merchant_role`),
    # before this body runs -- see merchant_dependencies.py.
    merchant_ctx=Depends(require_merchant_role(Vertical.ecommerce, READ_ROLES)),
    date_from: str | None = Query(None, description="ISO date (YYYY-MM-DD); defaults to the full order history"),
    date_to: str | None = Query(None, description="ISO date (YYYY-MM-DD); defaults to the full order history"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    error, merchant_uuid, _role_row = merchant_ctx
    if error is not None:
        return error
    error, parsed_from, parsed_to = _parse_dates(date_from, date_to)
    if error is not None:
        return error
    error, _ = await check_feature_access(current_user, "ecommerce.dashboard_summary")
    if error is not None:
        return error

    data, analysis_run_id, disabled_features = await compute_dashboard_summary(
        db, merchant_uuid, parsed_from, parsed_to
    )
    return success_response(data, disabled_features=disabled_features, analysis_run_id=analysis_run_id)


@router.get("/dashboard/revenue")
async def get_dashboard_revenue(
    merchant_ctx=Depends(require_merchant_role(Vertical.ecommerce, READ_ROLES)),
    date_from: str | None = Query(None, description="ISO date (YYYY-MM-DD); defaults to the full order history"),
    date_to: str | None = Query(None, description="ISO date (YYYY-MM-DD); defaults to the full order history"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    error, merchant_uuid, _role_row = merchant_ctx
    if error is not None:
        return error
    error, parsed_from, parsed_to = _parse_dates(date_from, date_to)
    if error is not None:
        return error
    error, _ = await check_feature_access(current_user, "ecommerce.net_margin_dashboard")
    if error is not None:
        return error

    data, analysis_run_id, missing_fields = await compute_dashboard_revenue(
        db, merchant_uuid, parsed_from, parsed_to
    )
    return success_response(data, analysis_run_id=analysis_run_id, missing_fields=missing_fields)
