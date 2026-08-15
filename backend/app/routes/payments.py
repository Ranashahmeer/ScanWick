import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import PaymentTransaction, Subscription, User
from app.schemas.envelope import error_response, success_response
from app.services import payments
from app.services.entitlements import FREE_TIER
from app.services.flutterwave_client import FlutterwaveAPIError
from app.services.paystack_client import PaystackAPIError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


class CheckoutRequest(BaseModel):
    tier: str


def _serialize_subscription(subscription: Subscription | None, user_tier: str) -> dict:
    if subscription is None:
        # No Subscription row yet (never checked out) — User.subscription_tier
        # is still the authoritative current tier (defaults to "free"), so
        # report that rather than guessing. `or FREE_TIER` guards the one
        # edge case where a caller hands in a falsy/unset value.
        return {
            "tier": user_tier or FREE_TIER,
            "status": None,
            "provider": None,
            "current_period_end": None,
            "cancel_at_period_end": False,
        }
    return {
        "tier": subscription.tier,
        "status": subscription.status.value,
        "provider": subscription.provider,
        "current_period_end": (
            subscription.current_period_end.isoformat() if subscription.current_period_end else None
        ),
        "cancel_at_period_end": subscription.cancel_at_period_end,
    }


def _serialize_transaction(transaction: PaymentTransaction) -> dict:
    return {
        "id": str(transaction.id),
        "provider": transaction.provider,
        "amount": str(transaction.amount),
        "currency": transaction.currency,
        "status": transaction.status.value,
        "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
    }


@router.post("/checkout")
async def checkout(
    body: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Starts a hosted-checkout transaction — tries Paystack first, falls
    back to Flutterwave if Paystack's API call fails (see
    `payments.initiate_checkout`). Only a 502 here means BOTH providers
    failed; the frontend just redirects the browser to `authorization_url`
    on success, no card handling happens on this side either way."""
    try:
        result = await payments.initiate_checkout(db, current_user, body.tier)
    except ValueError as exc:
        return JSONResponse(status_code=422, content=error_response("INVALID_TIER", str(exc)))
    except (PaystackAPIError, FlutterwaveAPIError):
        logger.exception("Both payment providers failed to start checkout for user %s", current_user.id)
        return JSONResponse(
            status_code=502,
            content=error_response("CHECKOUT_FAILED", "Could not start checkout. Please try again."),
        )
    return success_response({"authorization_url": result.authorization_url, "reference": result.reference})


@router.get("/verify/{reference}")
async def verify(
    reference: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eager check right after the browser redirects back from checkout —
    reflects a successful payment immediately instead of waiting on the
    webhook, using the same `apply_successful_charge` the webhook uses so
    the two paths can never disagree."""
    try:
        result_status = await payments.verify_and_apply(db, reference, current_user.id)
    except ValueError as exc:
        return JSONResponse(status_code=404, content=error_response("TRANSACTION_NOT_FOUND", str(exc)))
    except (PaystackAPIError, FlutterwaveAPIError):
        logger.exception("Verify failed for reference %s", reference)
        return JSONResponse(
            status_code=502, content=error_response("VERIFY_FAILED", "Could not verify this payment.")
        )
    return success_response({"status": result_status})


@router.get("/subscription")
async def get_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subscription = (
        await db.execute(select(Subscription).where(Subscription.user_id == current_user.id))
    ).scalar_one_or_none()
    return success_response(_serialize_subscription(subscription, current_user.subscription_tier))


@router.get("/history")
async def get_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transactions = (
        (
            await db.execute(
                select(PaymentTransaction)
                .where(PaymentTransaction.user_id == current_user.id)
                .order_by(PaymentTransaction.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return success_response([_serialize_transaction(t) for t in transactions])


@router.post("/cancel")
async def cancel(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await payments.request_cancellation(db, current_user)
    except ValueError as exc:
        return JSONResponse(status_code=400, content=error_response("NO_ACTIVE_SUBSCRIPTION", str(exc)))
    except (PaystackAPIError, FlutterwaveAPIError):
        logger.exception("Cancellation failed for user %s", current_user.id)
        return JSONResponse(
            status_code=502,
            content=error_response("CANCEL_FAILED", "Could not cancel your subscription. Please try again."),
        )
    return success_response({"cancel_at_period_end": True})
