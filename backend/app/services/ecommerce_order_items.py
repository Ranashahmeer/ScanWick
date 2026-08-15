import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order_items import OrderItem
from app.models.orders import Order

# Same threshold as 1.11's ingestion-time COGS-missing rule.
COGS_MISSING_DISABLE_THRESHOLD_PCT = 20.0


async def fetch_merchant_order_items(db: AsyncSession, merchant_id: uuid.UUID) -> list[tuple[OrderItem, Order]]:
    """order_items joined to their parent order, excluding is_anomalous
    orders. Shared by every order_items-based diagnostic/dashboard
    endpoint (profit-leaks, dead-stock, sku-matrix) rather than each one
    querying independently."""
    result = await db.execute(
        select(OrderItem, Order)
        .join(Order, OrderItem.order_id == Order.id)
        .where(Order.merchant_id == merchant_id, Order.is_anomalous.is_(False))
    )
    return result.all()


def compute_cogs_coverage(rows: list[tuple[OrderItem, Order]]) -> dict:
    """Same rule as 1.11's ingestion-time check, re-evaluated against
    already-persisted data rather than the original CSV — coverage can
    change over time as more orders get ingested, so it can't just be
    cached from ingestion time."""
    total = len(rows)
    missing = sum(1 for item, _ in rows if item.unit_cogs is None)
    missing_pct = round(missing / total * 100, 1) if total else 0.0
    disabled = total > 0 and missing_pct > COGS_MISSING_DISABLE_THRESHOLD_PCT
    return {"total_line_items": total, "missing_count": missing, "missing_pct": missing_pct, "disabled": disabled}
