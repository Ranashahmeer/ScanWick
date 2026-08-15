from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orders import Order
from app.models.reconciliation_reports import AnalyzerType
from app.services.ecommerce_revenue import aggregate_orders, resolve_period
from app.services.reconciliation import record_analysis_run

# Per spec's e-commerce validation rules: "Stale data (API mode): Last order
# > 24h ago -> Show Stale Data alert". Applied here regardless of source
# (CSV ingestion doesn't change what "stale" should mean to a merchant
# looking at their dashboard).
DATA_STALE_AFTER_HOURS = 24


def _change_pct(current: Decimal, previous: Decimal) -> Optional[float]:
    if previous == 0:
        return None
    return round(float((current - previous) / previous * 100), 1)


async def compute_dashboard_summary(
    db: AsyncSession, merchant_id: UUID, date_from: Optional[date], date_to: Optional[date]
) -> tuple[dict, str, list]:
    """GET /api/v1/ecommerce/dashboard/summary. Returns (data, analysis_run_id,
    disabled_features) — the route assembles the envelope from these."""
    start, end = await resolve_period(db, merchant_id, date_from, date_to)

    previous = None
    if start is None:
        current = {"gross_revenue": 0, "net_revenue": 0, "total_orders": 0, "currency": "NGN"}
        start = end = datetime.now(timezone.utc).date()
    else:
        current = await aggregate_orders(db, merchant_id, start, end)
        period_length_days = (end - start).days + 1
        prev_end = start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_length_days - 1)
        previous = await aggregate_orders(db, merchant_id, prev_start, prev_end)

    # Audit #31: this used to check Upload.created_at (upload recency)
    # despite the spec text above being about order recency — re-uploading
    # a file whose most recent order was months old would immediately
    # report is_stale=False, and it only ever flipped True 24h after the
    # *upload*, never reflecting how current the actual order data is.
    # Fixed to check max(Order.order_date) directly, matching the spec.
    last_order_date = (
        await db.execute(select(func.max(Order.order_date)).where(Order.merchant_id == merchant_id))
    ).scalar_one_or_none()
    if last_order_date is not None and last_order_date.tzinfo is None:
        # SQLite (the dev/test DB) silently strips tzinfo from
        # DateTime(timezone=True) columns on round-trip — Postgres
        # wouldn't lose it, but this must work on both. Treat a naive
        # value as UTC rather than crashing on an aware-vs-naive
        # subtraction.
        last_order_date = last_order_date.replace(tzinfo=timezone.utc)
    is_stale = (
        (datetime.now(timezone.utc) - last_order_date).total_seconds() > DATA_STALE_AFTER_HOURS * 3600
        if last_order_date
        else None
    )

    disabled_features = []

    report = await record_analysis_run(
        db,
        merchant_id,
        AnalyzerType.ecommerce,
        date_range_start=start,
        date_range_end=end,
        base_currency=current["currency"],
        records_analyzed=current["total_orders"],
        disabled_features=disabled_features,
    )

    data = {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "gross_revenue": {
            "value": current["gross_revenue"],
            "currency": current["currency"],
            "change_pct": _change_pct(current["gross_revenue"], previous["gross_revenue"]) if previous else None,
        },
        "net_revenue": {
            "value": current["net_revenue"],
            "currency": current["currency"],
            "change_pct": _change_pct(current["net_revenue"], previous["net_revenue"]) if previous else None,
        },
        "total_orders": current["total_orders"],
        "avg_order_value": (
            round(float(current["gross_revenue"] / current["total_orders"]), 2) if current["total_orders"] else 0.0
        ),
        "data_freshness": {
            "last_synced": last_order_date.isoformat() if last_order_date else None,
            "is_stale": is_stale,
        },
    }
    return data, str(report.id), disabled_features
