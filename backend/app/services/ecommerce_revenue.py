import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orders import Order
from app.models.reconciliation_reports import AnalyzerType
from app.services.merchant_currency import get_merchant_base_currency_or_default
from app.services.reconciliation import record_analysis_run


async def resolve_period(
    db: AsyncSession, merchant_id: uuid.UUID, date_from: Optional[date], date_to: Optional[date]
) -> tuple[Optional[date], Optional[date]]:
    """Explicit query params win; otherwise defaults to the full range of
    this merchant's non-anomalous order history — simpler and more
    predictable than inventing an arbitrary default window (e.g. "last 90
    days") spec doesn't actually specify. Shared by every ecommerce
    dashboard/diagnostic endpoint that takes an optional date range."""
    if date_from and date_to:
        return date_from, date_to
    bounds = (
        await db.execute(
            select(func.min(Order.order_date), func.max(Order.order_date)).where(
                Order.merchant_id == merchant_id, Order.is_anomalous.is_(False)
            )
        )
    ).one()
    min_date, max_date = bounds
    if min_date is None:
        return None, None
    return date_from or min_date.date(), date_to or max_date.date()


async def fetch_orders_in_range(db: AsyncSession, merchant_id: uuid.UUID, start: date, end: date) -> list[Order]:
    """Non-anomalous orders for this merchant within [start, end] (inclusive,
    whole days)."""
    result = await db.execute(
        select(Order).where(
            Order.merchant_id == merchant_id,
            Order.is_anomalous.is_(False),
            Order.order_date >= datetime.combine(start, time.min, tzinfo=timezone.utc),
            Order.order_date <= datetime.combine(end, time.max, tzinfo=timezone.utc),
        )
    )
    return list(result.scalars().all())


def aggregate_order_list(orders: list[Order], base_currency: str) -> dict:
    """Aggregate orders in the merchant's base currency.

    Only orders with a valid `exchange_rate_at_order` and a populated
    `base_currency_amount` contribute to converted totals. Orders missing
    conversion data are excluded from the base-currency sums and surfaced
    via meta missing_fields and quality metadata.
    """
    gross_revenue = 0
    returns = 0
    discounts = 0
    shipping = 0
    processing = 0
    ad_spend = 0
    missing_conversion_orders = 0

    for o in orders:
        if o.base_currency_amount is None or o.exchange_rate_at_order is None:
            if o.original_currency != base_currency:
                missing_conversion_orders += 1
                continue
            rate = 1
            order_gross = o.gross_revenue
        else:
            rate = o.exchange_rate_at_order
            order_gross = o.base_currency_amount

        gross_revenue += order_gross
        returns += (o.refund_amount or 0) * rate
        discounts += (o.discount_amount or 0) * rate
        shipping += (o.shipping_cost or 0) * rate
        processing += (o.processing_fees or 0) * rate
        ad_spend += (o.allocated_ad_spend or 0) * rate

    net_revenue = gross_revenue - returns - discounts - shipping - processing - ad_spend

    return {
        "gross_revenue": gross_revenue,
        "net_revenue": net_revenue,
        "total_orders": len(orders),
        "included_orders": len(orders) - missing_conversion_orders,
        "excluded_orders_due_to_missing_conversion": missing_conversion_orders,
        "currency": base_currency,
        "returns": returns,
        "discounts": discounts,
        "shipping": shipping,
        "processing": processing,
        "ad_spend": ad_spend,
    }


async def aggregate_orders(db: AsyncSession, merchant_id: uuid.UUID, start: date, end: date) -> dict:
    base_currency = await get_merchant_base_currency_or_default(db, merchant_id)
    return aggregate_order_list(await fetch_orders_in_range(db, merchant_id, start, end), base_currency)


def monthly_revenue_trend(orders: list[Order], base_currency: str) -> list[dict]:
    """Groups already-fetched orders by calendar month (YYYY-MM), per spec's
    monthly_trend shape, in base currency."""
    months: dict[str, dict] = {}
    for o in orders:
        if o.base_currency_amount is None or o.exchange_rate_at_order is None:
            if o.original_currency != base_currency:
                continue
            rate = 1
            base_amount = o.gross_revenue
        else:
            rate = o.exchange_rate_at_order
            base_amount = o.base_currency_amount

        key = o.order_date.strftime("%Y-%m")
        bucket = months.setdefault(key, {"gross": 0, "net": 0})
        bucket["gross"] += base_amount
        bucket["net"] += (
            base_amount
            - ((o.refund_amount or 0) * rate)
            - ((o.discount_amount or 0) * rate)
            - ((o.shipping_cost or 0) * rate)
            - ((o.processing_fees or 0) * rate)
            - ((o.allocated_ad_spend or 0) * rate)
        )
    return [
        {"month": month, "gross": bucket["gross"], "net": bucket["net"]} for month, bucket in sorted(months.items())
    ]


async def compute_dashboard_revenue(
    db: AsyncSession, merchant_id: uuid.UUID, date_from: Optional[date], date_to: Optional[date]
) -> tuple[dict, str, list[str]]:
    """GET /api/v1/ecommerce/dashboard/revenue. Returns (data, analysis_run_id)."""
    start, end = await resolve_period(db, merchant_id, date_from, date_to)
    if start is None:
        start = end = datetime.now(timezone.utc).date()
        orders: list[Order] = []
    else:
        orders = await fetch_orders_in_range(db, merchant_id, start, end)

    base_currency = await get_merchant_base_currency_or_default(db, merchant_id)
    totals = aggregate_order_list(orders, base_currency)

    missing_fields = []
    if totals["excluded_orders_due_to_missing_conversion"]:
        missing_fields.append("base_currency_amount")

    report = await record_analysis_run(
        db,
        merchant_id,
        AnalyzerType.ecommerce,
        date_range_start=start,
        date_range_end=end,
        base_currency=totals["currency"],
        records_analyzed=totals["total_orders"],
    )

    data = {
        "gross_revenue": totals["gross_revenue"],
        "net_revenue": totals["net_revenue"],
        "gap": totals["gross_revenue"] - totals["net_revenue"],
        "gap_breakdown": {
            "returns": totals["returns"],
            "discounts": totals["discounts"],
            "shipping": totals["shipping"],
            "processing": totals["processing"],
            "ad_spend": totals["ad_spend"],
        },
        "monthly_trend": monthly_revenue_trend(orders, base_currency),
        "currency": totals["currency"],
        "included_orders": totals["included_orders"],
        "excluded_orders_due_to_missing_conversion": totals["excluded_orders_due_to_missing_conversion"],
    }
    return data, str(report.id), missing_fields
