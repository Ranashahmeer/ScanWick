import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.merchant_settings import MerchantSettings


async def get_merchant_base_currency(db: AsyncSession, merchant_id: uuid.UUID) -> Optional[str]:
    """Reuses `merchant_settings.base_currency` — nominally under the spec's
    E-Commerce tables, but treated as a cross-analyzer merchant-level
    setting (a merchant operates in one base currency regardless of which
    analyzer is running), same as `uploads`/`contextual_markers`/
    `exchange_rates` are already shared rather than per-vertical. `None`
    (not a fabricated default) when no settings row exists yet — callers
    that need currency-conversion logic to distinguish "unknown" from "set
    to X" should use this; callers that just need a display label should
    use `get_merchant_base_currency_or_default`."""
    result = await db.execute(select(MerchantSettings.base_currency).where(MerchantSettings.merchant_id == merchant_id))
    return result.scalar_one_or_none()


async def get_merchant_base_currency_or_default(db: AsyncSession, merchant_id: uuid.UUID, default: str = "NGN") -> str:
    return await get_merchant_base_currency(db, merchant_id) or default
