from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import (
    Account,
    Order,
    PaymentTransaction,
    Subscription,
    Upload,
    User,
)
from app.schemas.envelope import success_response
from app.services.merchant_provisioning import ensure_merchant_provisioned
from app.services.privacy import delete_all_merchant_data

router = APIRouter(prefix="/api/v1/privacy", tags=["privacy"])


@router.get("/export")
async def export_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Synchronous export — built directly in the request, no job queue.
    Bundles the account profile plus every dataset the user has uploaded or
    that's been derived from it, so "download my data" actually returns
    something meaningful rather than a stub."""
    merchant_id = await ensure_merchant_provisioned(db, current_user.id)

    uploads = (
        (await db.execute(select(Upload).where(Upload.merchant_id == merchant_id))).scalars().all()
    )
    order_count = (
        await db.execute(select(func.count()).select_from(Order).where(Order.merchant_id == merchant_id))
    ).scalar_one()
    account_count = (
        await db.execute(select(func.count()).select_from(Account).where(Account.user_id == merchant_id))
    ).scalar_one()
    subscription = (
        await db.execute(select(Subscription).where(Subscription.user_id == current_user.id))
    ).scalar_one_or_none()
    transactions = (
        (
            await db.execute(
                select(PaymentTransaction).where(PaymentTransaction.user_id == current_user.id)
            )
        )
        .scalars()
        .all()
    )

    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "profile": {
            "email": current_user.email,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "company": current_user.company,
            "company_size": current_user.company_size,
            "industry": current_user.industry,
            "primary_currency": current_user.primary_currency,
            "language": current_user.language,
            "timezone": current_user.timezone,
            "subscription_tier": current_user.subscription_tier,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        },
        "uploads": [
            {
                "upload_id": str(upload.id),
                "analyzer_type": upload.analyzer_type.value,
                "data_source": upload.data_source,
                "status": upload.status.value,
                "rows_parsed": upload.rows_parsed,
                "created_at": upload.created_at.isoformat() if upload.created_at else None,
            }
            for upload in uploads
        ],
        "data_summary": {
            "orders": order_count,
            "bank_accounts": account_count,
        },
        "subscription": {
            "tier": subscription.tier if subscription else current_user.subscription_tier,
            "status": subscription.status.value if subscription else None,
            "provider": subscription.provider if subscription else None,
        },
        "billing_history": [
            {
                "id": str(transaction.id),
                "provider": transaction.provider,
                "amount": str(transaction.amount),
                "currency": transaction.currency,
                "status": transaction.status.value,
                "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
            }
            for transaction in transactions
        ],
    }

    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": "attachment; filename=scanwick-data-export.json"},
    )


@router.post("/delete-data")
async def delete_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    merchant_id = await ensure_merchant_provisioned(db, current_user.id)
    await delete_all_merchant_data(db, current_user.id, merchant_id)
    return success_response({"deleted": True})
