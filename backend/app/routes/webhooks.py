"""Inbound webhook endpoints from third-party providers — kept in their own
router (`/api/v1/webhooks/*`, separate from `/api/v1/payments/*`) since
these are called by Paystack/Flutterwave directly, not by this app's own
frontend, and carry no user authentication at all (identity here comes from
the request's signature, not a Bearer token)."""
import logging

from fastapi import APIRouter, Header, Request, status
from fastapi.responses import JSONResponse

from app.schemas.envelope import error_response
from app.services import payments

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/paystack", status_code=status.HTTP_200_OK)
async def paystack_webhook(request: Request, x_paystack_signature: str | None = Header(default=None)):
    """No auth dependency — Paystack calls this directly. Reads the RAW body
    (required for signature verification, must happen before any JSON
    parsing), verifies it, then hands off to Celery and returns 200
    immediately so Paystack never times out and retries the same event."""
    raw_body = await request.body()
    if not payments.verify_paystack_signature(raw_body, x_paystack_signature):
        return JSONResponse(
            status_code=401, content=error_response("INVALID_SIGNATURE", "Signature verification failed.")
        )

    payload = await request.json()
    payments.process_paystack_webhook_task.delay(payload)
    return {"received": True}


@router.post("/flutterwave", status_code=status.HTTP_200_OK)
async def flutterwave_webhook(request: Request, verif_hash: str | None = Header(default=None, alias="verif-hash")):
    """No auth dependency — Flutterwave calls this directly. Flutterwave's
    verification is a direct header compare (no HMAC), unlike Paystack's —
    see `payments.verify_flutterwave_signature`."""
    if not payments.verify_flutterwave_signature(verif_hash):
        return JSONResponse(
            status_code=401, content=error_response("INVALID_SIGNATURE", "Signature verification failed.")
        )

    payload = await request.json()
    payments.process_flutterwave_webhook_task.delay(payload)
    return {"received": True}
