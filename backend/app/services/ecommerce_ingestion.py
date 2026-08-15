import asyncio
import hashlib
import uuid
from decimal import Decimal
from typing import Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery_app
from app.database import async_session
from app.models.merchant_settings import MerchantSettings
from app.models.order_items import OrderItem
from app.models.orders import Order, OrderDataSource, OrderStatus
from app.models.reconciliation_reports import AnalyzerType
from app.models.uploads import Upload, UploadStatus
from app.services.column_mapping import summarize_mapping_applied
from app.services.contextual_markers import get_marker_ranges, is_within_marker_ranges
from app.services.ecommerce_margins import compute_net_margin, resolve_unit_return_cost
from app.services.exchange_rates import get_historical_rate
from app.services.upload_staging import (
    delete_staged_upload,
    mark_upload_failed,
    read_staged_upload,
)
from app.utils.analyzer import COLUMN_CANDIDATES, find_column
from app.utils.locale_dates import parse_locale_date
from app.utils.numeric import parse_kobo as _kobo_or_none

# Above this percentage of line items missing unit_cogs, unit margin and
# profit leak detection are disabled per spec.
COGS_MISSING_DISABLE_THRESHOLD_PCT = 20.0

# Explicit literal headers from each platform's standard order export. These are
# tried first since they're reliable for known-source data; `find_column` (the
# existing fuzzy keyword matcher from utils/analyzer.py) is only used as a
# fallback for the handful of canonical fields that overlap with its existing
# roles (amount, date, qty) — not duplicated for fields with no real overlap
# (e.g. sku, channel).
SHOPIFY_COLUMN_MAP = {
    "external_order_id": "Name",
    "order_date": "Created at",
    "gross_revenue": "Total",
    "original_currency": "Currency",
    "discount_amount": "Discount Amount",
    "refund_amount": "Refunded Amount",
    "shipping_cost": "Shipping",
    "channel": "Source Name",
    "sku": "Lineitem sku",
    "quantity": "Lineitem quantity",
    "unit_price": "Lineitem price",
    # Not a standard Shopify export column — picked up opportunistically if a
    # merchant has added one. Standard exports will have this 100% missing,
    # which is exactly the gap the quality-report COGS rule is meant to surface.
    "unit_cogs": "Lineitem cogs",
    # SKU-level return-cost override (order_items.unit_return_cost per spec) —
    # also not a standard export column, same opportunistic note.
    "unit_return_cost": "Lineitem return cost",
    # Real, standard Shopify export column — unlike unit_cogs/unit_return_cost
    # above, this one is genuinely present in default exports. Added for
    # task 3.3 (RFM clustering needs real per-customer identity; orders.
    # customer_id has been an unconstrained, always-null UUID since 1.7 with
    # no customers table and no ingestion path populating it). Hashed into a
    # deterministic UUID (see _resolve_customer_id) rather than changing the
    # column's type.
    "customer_email": "Email",
}

WOOCOMMERCE_COLUMN_MAP = {
    "external_order_id": "order_id",
    "order_date": "order_date",
    "gross_revenue": "order_total",
    "original_currency": "order_currency",
    "discount_amount": "cart_discount",
    "refund_amount": "refunded_total",
    "shipping_cost": "order_shipping",
    "channel": "payment_method",
    "sku": "item_sku",
    "quantity": "item_quantity",
    "unit_price": "item_cost",
    # Not a standard WooCommerce export column — same opportunistic note as Shopify.
    "unit_cogs": "item_cost_price",
    "unit_return_cost": "item_return_cost",
    # Real, standard WooCommerce export column — same task-3.3 customer-identity
    # note as Shopify's "Email" above.
    "customer_email": "billing_email",
}

# Scanwick's own canonical-field-named export (e.g. scanwick_test_ecommerce_orders.csv,
# ecommerce_orders_10k_updated.csv) -- unlike Shopify/WooCommerce, column names
# here are literally this model's own field names, so the map is closer to an
# identity mapping. Added because neither Shopify's nor WooCommerce's fixed
# literal headers happen to match this shape at all (verified directly: under
# either existing map, `sku`/`unit_cogs`/`customer_email`/`original_currency`
# all resolve to None for these files, and `gross_revenue` incorrectly
# resolves to whichever column contains "price" first) -- not a hypothetical
# gap, an empirically-confirmed one.
GENERIC_COLUMN_MAP = {
    "external_order_id": "order_id",
    "order_date": "order_date",
    "gross_revenue": "gross_revenue",
    "original_currency": "currency",
    "discount_amount": "discount_amount",
    "refund_amount": "refund_amount",
    "shipping_cost": "shipping_cost",
    "processing_fees": "processing_fee",
    "allocated_ad_spend": "ad_spend_allocated",
    "channel": "channel",
    "sku": "sku",
    "quantity": "quantity",
    "unit_price": "unit_price",
    "unit_cogs": "cogs",
    "unit_return_cost": "unit_return_cost",
    "customer_email": "customer_email",
}

# Canonical fields where falling back to the existing fuzzy column-detection
# logic makes sense because a matching role already exists there.
_FALLBACK_ROLE = {
    "gross_revenue": "amount",
    "order_date": "date",
    "quantity": "qty",
    "unit_price": "amount",
}


def score_ecommerce_columns(df: pd.DataFrame) -> tuple[float, OrderDataSource]:
    """How closely this dataframe's columns match a known e-commerce export
    format — used by dataset_detection.py to auto-identify an uploaded
    file's type before the user has to say so. Checks literal header
    presence only (not the fuzzy _FALLBACK_ROLE matching _resolve_column
    also does during real ingestion) — detection needs to tell formats
    apart from bank/sales exports, not maximize field coverage within an
    already-known format. Returns (best score, which format matched)."""
    best_score = 0.0
    best_source = OrderDataSource.generic_csv
    for source, column_map in (
        (OrderDataSource.shopify_csv, SHOPIFY_COLUMN_MAP),
        (OrderDataSource.woocommerce_csv, WOOCOMMERCE_COLUMN_MAP),
        (OrderDataSource.generic_csv, GENERIC_COLUMN_MAP),
    ):
        resolved = sum(1 for col in column_map.values() if col in df.columns)
        score = resolved / len(column_map)
        if score > best_score:
            best_score = score
            best_source = source
    return best_score, best_source


def _resolve_column(df: pd.DataFrame, canonical_field: str, column_map: dict) -> Optional[str]:
    exact = column_map.get(canonical_field)
    if exact and exact in df.columns:
        return exact

    fallback_role = _FALLBACK_ROLE.get(canonical_field)
    if fallback_role:
        return find_column(df, COLUMN_CANDIDATES[fallback_role])
    return None



def _resolve_shopify_status(financial_status: str, fulfillment_status: str) -> OrderStatus:
    fin = (financial_status or "").strip().lower()
    ful = (fulfillment_status or "").strip().lower()
    if fin in ("refunded", "partially_refunded"):
        return OrderStatus.refunded
    if fin == "voided":
        return OrderStatus.cancelled
    if ful == "fulfilled":
        return OrderStatus.fulfilled
    return OrderStatus.pending


def _resolve_woocommerce_status(raw_status: str) -> OrderStatus:
    status = (raw_status or "").strip().lower().removeprefix("wc-")
    if status == "completed":
        return OrderStatus.fulfilled
    if status == "refunded":
        return OrderStatus.refunded
    if status in ("cancelled", "failed"):
        return OrderStatus.cancelled
    return OrderStatus.pending


def _resolve_generic_status(refund_amount: Optional[Decimal]) -> OrderStatus:
    """The generic/canonical export has no separate order-status column at
    all (unlike Shopify's Financial/Fulfillment Status or WooCommerce's
    `status`) -- derived from refund_amount, a field the row already carries,
    rather than defaulting every row to the same status regardless of data."""
    if refund_amount and refund_amount > 0:
        return OrderStatus.refunded
    return OrderStatus.fulfilled


def _normalize_external_id(value) -> Optional[str]:
    """3.6: the old `str(raw.get(col))` turned a genuinely-missing cell
    (NaN, since pandas leaves numeric-looking ID columns as float64) into
    the literal string "nan" -- present, not missing, so no surrogate ID
    was ever generated for it and, worse, every such row collided with
    every other one on that same literal "nan" key. Same notna-then-strip
    shape as `customer_email`'s handling a few lines down. Only trims
    whitespace -- the platform's own casing (e.g. Shopify's "#1001") is
    preserved for storage/display; see `_dedup_key` for the
    casefolded-for-comparison form."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def _dedup_key(external_id: str) -> str:
    """3.6: "normalize IDs before comparison" -- case-only differences
    ("ORD-001" vs "ord-001") must be recognized as the same order without
    changing what's actually stored in `external_order_id` (unlike
    `_normalize_external_id`, which only fixes the NaN/whitespace case).
    Comparison-only; never write this value to the DB."""
    return external_id.casefold()


def _generate_surrogate_external_id(
    merchant_id: uuid.UUID,
    source: OrderDataSource,
    row_position: int,
    order_date,
    sku: Optional[str],
    quantity: Optional[int],
    gross_revenue: Optional[Decimal],
) -> str:
    """3.6: rows with no external_order_id in the source export used to be
    permanently re-insertable on every re-upload (the dedup check was
    skipped entirely whenever external_order_id was None). Builds a stable
    surrogate ID instead, from fields that are identical across two
    ingests of the *same* file -- merchant, source format, this row's own
    position in the file (stable for an unmodified re-upload, since
    extraction preserves row order), and the row's own date/SKU/quantity/
    revenue.

    Collision policy: two DIFFERENT rows that happen to share every one of
    these six fields exactly (same merchant, source, position, date, SKU,
    quantity, and revenue) hash to the same surrogate ID and the second is
    treated as a duplicate of the first and skipped -- the same outcome a
    real duplicate would produce, and, for two rows this
    indistinguishable, an explicit and defensible one.
    """
    date_part = order_date.date().isoformat() if order_date is not None else "unknown-date"
    payload = "|".join(
        [
            str(merchant_id),
            source.value,
            str(row_position),
            date_part,
            (sku or "").strip().lower(),
            str(quantity) if quantity is not None else "",
            str(gross_revenue) if gross_revenue is not None else "",
        ]
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()[:32]
    return f"surrogate:{digest}"


def extract_canonical_rows(
    df: pd.DataFrame,
    source: OrderDataSource,
    mapping: Optional[dict[str, str]] = None,
    value_rules: Optional[dict] = None,
) -> list[dict]:
    """Map a Shopify, WooCommerce, or Scanwick-generic order-export dataframe
    into canonical row dicts — one per CSV row. All three sources feed this
    same function and produce the same dict shape; only the column lookup
    differs.

    `mapping` (Data Mapping Layer, {user_header: canonical_field}, confirmed
    via POST /api/v1/mapping/confirm or auto-applied by
    app/services/column_mapping.py) takes priority over the hardcoded
    per-platform maps below when provided — any caller not going through
    that new flow (tests, direct calls) is unaffected, since it defaults to
    None and falls back to today's exact behavior.

    Simplification: treats each CSV row as one order with exactly one line
    item. Real Shopify exports repeat a row per line item under the same
    order `Name` — multi-line-item aggregation is a follow-on refinement, not
    handled here.
    """
    if source == OrderDataSource.shopify_csv:
        column_map = SHOPIFY_COLUMN_MAP
    elif source == OrderDataSource.woocommerce_csv:
        column_map = WOOCOMMERCE_COLUMN_MAP
    else:
        column_map = GENERIC_COLUMN_MAP

    if mapping:
        override_map = {canonical: header for header, canonical in mapping.items()}
        # GENERIC_COLUMN_MAP is the superset of every canonical field this
        # function reads below (Shopify's/WooCommerce's maps are each
        # missing a few, e.g. processing_fees/allocated_ad_spend) -- always
        # resolving against that full field list, not just `column_map`'s,
        # so nothing downstream KeyErrors regardless of which map would have
        # applied without an override.
        resolved = {
            field: (override_map.get(field) if override_map.get(field) in df.columns else None)
            for field in GENERIC_COLUMN_MAP
        }
    else:
        resolved = {field: _resolve_column(df, field, column_map) for field in column_map}
    # processing_fees/allocated_ad_spend only exist in the generic map -- absent
    # for Shopify/WooCommerce, same as any other unresolved field (stays None).
    processing_fees_col = resolved.get("processing_fees")
    allocated_ad_spend_col = resolved.get("allocated_ad_spend")
    per_unit_revenue = bool(value_rules) and value_rules.get("gross_revenue") == "per_unit"
    # 3.7: read from the mapping's persisted value_rules; parse_locale_date
    # falls back to the documented day-first default only when absent.
    date_locale = (value_rules or {}).get("date_locale")

    rows = []
    for row_position, (_, raw) in enumerate(df.iterrows()):
        order_date = None
        date_warning = None
        if resolved["order_date"]:
            order_date, date_warning = parse_locale_date(raw.get(resolved["order_date"]), date_locale)
            if date_warning is not None:
                date_warning = {**date_warning, "row": row_position, "field": "order_date"}

        if source == OrderDataSource.shopify_csv:
            status = _resolve_shopify_status(raw.get("Financial Status"), raw.get("Fulfillment Status"))
        elif source == OrderDataSource.woocommerce_csv:
            status = _resolve_woocommerce_status(raw.get("status"))
        else:
            status = _resolve_generic_status(_kobo_or_none(raw.get(resolved["refund_amount"])) if resolved["refund_amount"] else None)

        raw_quantity = int(raw[resolved["quantity"]]) if resolved["quantity"] and pd.notna(raw.get(resolved["quantity"])) else None
        raw_gross_revenue = _kobo_or_none(raw.get(resolved["gross_revenue"])) if resolved["gross_revenue"] else None
        # Data Mapping Layer's per-unit-vs-line-total value_question: when the
        # confirmed answer is "per_unit", the mapped column is a unit price,
        # not the order/line total -- multiply by quantity to get the real
        # total. Default (line_total, or no value_rules at all) matches
        # every existing caller's behavior unchanged.
        gross_revenue = (
            raw_gross_revenue * raw_quantity
            if per_unit_revenue and raw_gross_revenue is not None and raw_quantity is not None
            else raw_gross_revenue
        )

        rows.append(
            {
                "external_order_id": (
                    _normalize_external_id(raw.get(resolved["external_order_id"]))
                    if resolved["external_order_id"]
                    else None
                ),
                "order_date": order_date.to_pydatetime() if order_date is not None and not pd.isna(order_date) else None,
                "_row_warning": date_warning,
                "gross_revenue": gross_revenue,
                "original_currency": raw.get(resolved["original_currency"]) if resolved["original_currency"] else None,
                "discount_amount": _kobo_or_none(raw.get(resolved["discount_amount"])) if resolved["discount_amount"] else None,
                "refund_amount": _kobo_or_none(raw.get(resolved["refund_amount"])) if resolved["refund_amount"] else None,
                "shipping_cost": _kobo_or_none(raw.get(resolved["shipping_cost"])) if resolved["shipping_cost"] else None,
                "processing_fees": _kobo_or_none(raw.get(processing_fees_col)) if processing_fees_col else None,
                "allocated_ad_spend": _kobo_or_none(raw.get(allocated_ad_spend_col)) if allocated_ad_spend_col else None,
                "channel": raw.get(resolved["channel"]) if resolved["channel"] else None,
                "status": status,
                "sku": raw.get(resolved["sku"]) if resolved["sku"] else None,
                "quantity": raw_quantity,
                "unit_price": _kobo_or_none(raw.get(resolved["unit_price"])) if resolved["unit_price"] else None,
                "unit_cogs": _kobo_or_none(raw.get(resolved["unit_cogs"])) if resolved["unit_cogs"] else None,
                "unit_return_cost": (
                    _kobo_or_none(raw.get(resolved["unit_return_cost"])) if resolved["unit_return_cost"] else None
                ),
                "customer_email": (
                    str(raw.get(resolved["customer_email"])).strip()
                    if resolved["customer_email"] and pd.notna(raw.get(resolved["customer_email"]))
                    else None
                ),
            }
        )
    return rows


# Fixed namespace for deriving a deterministic customer_id UUID from an
# email address — same email always hashes to the same UUID, so repeat
# customers are recognized as the same customer across orders/ingestion
# runs, without changing orders.customer_id's column type.
_CUSTOMER_ID_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d")


def resolve_customer_id(email: Optional[str]) -> Optional[uuid.UUID]:
    if not email:
        return None
    return uuid.uuid5(_CUSTOMER_ID_NAMESPACE, email.lower())


def _is_row_rejected(row: dict) -> bool:
    """A row can't become an Order without these — both columns are NOT NULL
    in the orders table. Missing either means the row is unusable, not a
    silent zero-fill."""
    return row["gross_revenue"] is None or row["order_date"] is None


async def _resolve_merchant_settings(db: AsyncSession, merchant_id: uuid.UUID) -> Optional[MerchantSettings]:
    result = await db.execute(select(MerchantSettings).where(MerchantSettings.merchant_id == merchant_id))
    return result.scalar_one_or_none()


async def write_canonical_rows(
    db: AsyncSession, canonical_rows: list[dict], merchant_id: uuid.UUID, source: OrderDataSource
) -> dict:
    """Writes already-extracted canonical rows. Split out from
    `ingest_dataframe` so the Celery task can extract once and both write and
    compute the quality report from the same rows, instead of parsing twice.

    Also applies, per spec: currency conversion at order_date (the historical
    rate, never "today's" rate) and contextual-marker is_anomalous flagging.
    Both lookups (merchant base currency, marker ranges) happen once for the
    whole batch, not once per row.
    """
    merchant_settings = await _resolve_merchant_settings(db, merchant_id)
    base_currency = merchant_settings.base_currency if merchant_settings else None
    merchant_default_return_cost = merchant_settings.default_return_cost if merchant_settings else None
    marker_ranges = await get_marker_ranges(db, merchant_id, AnalyzerType.ecommerce)

    # Audit #14 / 3.6: re-uploading the same export (or a client retry) used
    # to blindly insert a new Order for every row without an
    # external_order_id, silently doubling revenue/pipeline figures --
    # `_generate_surrogate_external_id` below now gives every such row a
    # stable ID too, so this same in-memory pre-check catches those re-uploads
    # as well. Scoped by data_source, matching `uq_orders_merchant_source_external_id`
    # (a genuine cross-platform ID collision, e.g. Shopify "1001" vs a manual
    # generic-CSV "1001", is not the same order). One query fetches this
    # merchant+source's already-ingested IDs up front so the per-row check
    # below is an in-memory set lookup, not a second query per row.
    existing_order_ids = {
        _dedup_key(row[0])
        for row in (
            await db.execute(
                select(Order.external_order_id).where(
                    Order.merchant_id == merchant_id,
                    Order.data_source == source,
                    Order.external_order_id.is_not(None),
                )
            )
        ).all()
    }

    orders_created = 0
    items_created = 0
    rows_rejected = 0
    duplicates_skipped = 0
    return_cost_defaulted_count = 0
    pending: list[tuple[Order, Optional[OrderItem]]] = []
    # Audit #19: get_historical_rate was previously awaited once per row —
    # memoized per unique (currency, date) pair actually seen in this batch.
    rate_cache: dict[tuple[str, object], Optional[Decimal]] = {}
    for row_position, row in enumerate(canonical_rows):
        if _is_row_rejected(row):
            rows_rejected += 1
            continue

        external_id = row["external_order_id"] or _generate_surrogate_external_id(
            merchant_id, source, row_position, row["order_date"], row["sku"], row["quantity"], row["gross_revenue"]
        )
        dedup_key = _dedup_key(external_id)
        if dedup_key in existing_order_ids:
            duplicates_skipped += 1
            continue
        existing_order_ids.add(dedup_key)

        original_currency = row["original_currency"] or "NGN"
        order_date_only = row["order_date"].date()

        # Falls back to the order's own currency (rate=1.0, no real
        # conversion) when the merchant hasn't onboarded a base_currency yet
        # — better than leaving every order's conversion fields null.
        effective_base_currency = base_currency or original_currency
        rate_key = (original_currency, order_date_only)
        if rate_key not in rate_cache:
            rate_cache[rate_key] = await get_historical_rate(
                db, original_currency, effective_base_currency, order_date_only
            )
        exchange_rate = rate_cache[rate_key]
        base_currency_amount = (row["gross_revenue"] * exchange_rate) if exchange_rate is not None else None

        # One item per order (1.10's documented simplification), so the
        # order-level cogs/return_cost are just this single item's
        # contribution — no real aggregation needed yet, but written so a
        # future multi-item order would just sum across items instead.
        resolved_return_cost = 0
        order_cogs = None
        item_fields: Optional[dict] = None
        if row["sku"]:
            quantity = row["quantity"] or 0
            unit_return_cost, defaulted_to_zero = resolve_unit_return_cost(
                row["unit_return_cost"], merchant_default_return_cost
            )
            if defaulted_to_zero:
                return_cost_defaulted_count += 1
            resolved_return_cost = unit_return_cost * quantity

            unit_shipping_cost = row["shipping_cost"]  # fully prorated onto the single item
            unit_net_margin = None
            if row["unit_cogs"] is not None:
                unit_net_margin = compute_net_margin(
                    gross_revenue=row["unit_price"] or 0,
                    cogs=row["unit_cogs"],
                    shipping_cost=unit_shipping_cost,
                    return_cost=unit_return_cost,
                )
                order_cogs = row["unit_cogs"] * quantity

            item_fields = dict(
                sku=row["sku"],
                quantity=quantity,
                unit_price=row["unit_price"] or 0,
                unit_cogs=row["unit_cogs"],
                unit_shipping_cost=unit_shipping_cost,
                unit_return_cost=row["unit_return_cost"],
                unit_net_margin=unit_net_margin,
            )

        net_margin = compute_net_margin(
            gross_revenue=row["gross_revenue"],
            refund_amount=row["refund_amount"],
            discount_amount=row["discount_amount"],
            cogs=order_cogs,
            shipping_cost=row["shipping_cost"],
            return_cost=resolved_return_cost,
        )

        order = Order(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            external_order_id=external_id,
            order_date=row["order_date"],
            gross_revenue=row["gross_revenue"],
            original_currency=original_currency,
            base_currency_amount=base_currency_amount,
            exchange_rate_at_order=exchange_rate,
            discount_amount=row["discount_amount"],
            refund_amount=row["refund_amount"],
            shipping_cost=row["shipping_cost"],
            processing_fees=row.get("processing_fees"),
            allocated_ad_spend=row.get("allocated_ad_spend"),
            cogs=order_cogs,
            net_margin=net_margin,
            channel=row["channel"],
            customer_id=resolve_customer_id(row.get("customer_email")),
            status=row["status"],
            data_source=source,
            is_anomalous=is_within_marker_ranges(order_date_only, marker_ranges),
        )
        item = OrderItem(id=uuid.uuid4(), order_id=order.id, merchant_id=merchant_id, **item_fields) if item_fields is not None else None
        pending.append((order, item))

    orders_created, items_created, race_duplicates = await _commit_pending_orders(db, pending)
    return {
        "orders_created": orders_created,
        "items_created": items_created,
        "rows_rejected": rows_rejected,
        "duplicates_skipped": duplicates_skipped + race_duplicates,
        "return_cost_defaulted_count": return_cost_defaulted_count,
    }


async def _commit_pending_orders(
    db: AsyncSession, pending: list[tuple[Order, Optional[OrderItem]]]
) -> tuple[int, int, int]:
    """3.6: commits the batch in one round trip in the common case. The
    in-memory pre-check above already rules out duplicates against what
    this process itself has seen, but a genuinely concurrent ingest for the
    same merchant+source (two overlapping requests, or a Celery task retry
    racing its own first attempt) can still commit an overlapping
    external_order_id between our SELECT and our INSERT --
    `uq_orders_merchant_source_external_id` is the actual backstop for
    that. On conflict, roll back the whole batch and retry row-by-row in
    savepoints so only the genuinely-colliding row(s) are dropped, not the
    rest of an otherwise-new batch -- makes a retried request idempotent
    rather than erroring or double-counting.
    """
    for order, item in pending:
        db.add(order)
        if item is not None:
            db.add(item)
    try:
        await db.commit()
        return len(pending), sum(1 for _, item in pending if item is not None), 0
    except IntegrityError:
        await db.rollback()

    orders_created = 0
    items_created = 0
    race_duplicates = 0
    for order, item in pending:
        try:
            async with db.begin_nested():
                db.add(order)
                if item is not None:
                    db.add(item)
                await db.flush()
        except IntegrityError:
            race_duplicates += 1
            continue
        orders_created += 1
        if item is not None:
            items_created += 1
    await db.commit()
    return orders_created, items_created, race_duplicates


async def ingest_dataframe(
    db: AsyncSession,
    df: pd.DataFrame,
    merchant_id: uuid.UUID,
    source: OrderDataSource,
    mapping: Optional[dict[str, str]] = None,
    value_rules: Optional[dict] = None,
) -> dict:
    """Core ingestion logic: parse + write canonical Order/OrderItem rows.
    Shared by both Shopify and WooCommerce — one analysis path, not two.
    Rows missing gross_revenue or order_date are rejected (not written) rather
    than silently zero-filled or crashing on the NOT NULL constraint."""
    canonical_rows = extract_canonical_rows(df, source, mapping, value_rules)
    return await write_canonical_rows(db, canonical_rows, merchant_id, source)


def compute_ecommerce_quality_report(canonical_rows: list[dict]) -> dict:
    """Data-quality report per spec: rows_parsed, rows_rejected, date_range,
    days_of_history, plus the COGS>=20%-missing disable rule. Operates on
    already-extracted canonical rows so it shares the exact same rejection
    criteria as `ingest_dataframe` — the report describes what actually got
    written, not a separate pass with its own rules."""
    parsed_rows = [r for r in canonical_rows if not _is_row_rejected(r)]
    rejected_row_objs = [r for r in canonical_rows if _is_row_rejected(r)]
    rows_rejected = len(rejected_row_objs)
    # 3.6: "include ... rejected counts and reasons in the quality report" --
    # a rejected row can be missing either or both of the two NOT NULL
    # fields; counted independently rather than as mutually-exclusive
    # buckets, so both reasons are visible for a row missing both.
    rejected_reasons = {
        "missing_gross_revenue": sum(1 for r in rejected_row_objs if r["gross_revenue"] is None),
        "missing_order_date": sum(1 for r in rejected_row_objs if r["order_date"] is None),
    }
    # 3.7: "every rejected row must produce a named warning with row
    # reference, canonical field, reason/code, raw value only when safe,
    # and remediation" -- `_row_warning` (set by extract_canonical_rows for
    # an AMBIGUOUS_DATE/INVALID_DATE cell) already has that shape; a row
    # rejected for a plain missing gross_revenue/order_date (no detection
    # column at all, or a genuinely blank cell) gets an equivalent
    # synthesized one so no rejected row is ever unaccounted for.
    rejected_rows = []
    for row_position, row in enumerate(canonical_rows):
        if not _is_row_rejected(row):
            continue
        warning = row.get("_row_warning")
        if warning is not None:
            rejected_rows.append(warning)
            continue
        missing_fields = [
            field for field, present in (("order_date", row["order_date"]), ("gross_revenue", row["gross_revenue"])) if present is None
        ]
        rejected_rows.append(
            {
                "row": row_position,
                "field": "/".join(missing_fields),
                "code": "MISSING_REQUIRED_FIELD",
                "message": f"Row {row_position} could not be resolved: missing {', '.join(missing_fields)}.",
                "raw_value": None,
                "remediation": "Confirm the column mapping for this field and re-upload.",
            }
        )

    order_dates = [r["order_date"] for r in parsed_rows]
    date_range_start = min(order_dates).date() if order_dates else None
    date_range_end = max(order_dates).date() if order_dates else None
    days_of_history = (date_range_end - date_range_start).days + 1 if date_range_start and date_range_end else 0

    line_items = [r for r in parsed_rows if r["sku"]]
    total_line_items = len(line_items)
    cogs_missing_count = sum(1 for r in line_items if r["unit_cogs"] is None)
    cogs_missing_pct = round(cogs_missing_count / total_line_items * 100, 1) if total_line_items else 0.0

    warnings = []
    if total_line_items > 0 and cogs_missing_pct > COGS_MISSING_DISABLE_THRESHOLD_PCT:
        warnings.append(
            {
                "field": "cogs",
                "severity": "high",
                "message": (
                    f"COGS is missing for {cogs_missing_count} of {total_line_items} line items "
                    f"({cogs_missing_pct}%). This exceeds the 20% threshold. Unit margin and "
                    "profit leak features are disabled."
                ),
                "features_disabled": ["unit_margin", "profit_leak_detector"],
            }
        )

    return {
        "rows_parsed": len(parsed_rows),
        "rows_rejected": rows_rejected,
        "rejected_reasons": rejected_reasons,
        "rejected_rows": rejected_rows,
        "date_range_start": date_range_start,
        "date_range_end": date_range_end,
        "days_of_history": days_of_history,
        "warnings": warnings,
    }


@celery_app.task(name="ingest_ecommerce_csv")
def ingest_ecommerce_csv(
    upload_id: str,
    merchant_id: str,
    source: str = OrderDataSource.shopify_csv.value,
    mapping: Optional[dict[str, str]] = None,
    value_rules: Optional[dict] = None,
) -> dict:
    return asyncio.run(_ingest_ecommerce_csv_async(upload_id, merchant_id, source, mapping, value_rules))


async def _ingest_ecommerce_csv_async(
    upload_id: str, merchant_id: str, source: str, mapping: Optional[dict[str, str]] = None, value_rules: Optional[dict] = None
) -> dict:
    try:
        df = read_staged_upload(upload_id)
        return await _ingest_ecommerce_csv_inner(df, upload_id, merchant_id, source, mapping, value_rules)
    except Exception as exc:
        async with async_session() as db:
            await mark_upload_failed(db, upload_id, uuid.UUID(merchant_id), AnalyzerType.ecommerce, exc)
        raise
    finally:
        delete_staged_upload(upload_id)


async def _ingest_ecommerce_csv_inner(
    df, upload_id: str, merchant_id: str, source: str, mapping: Optional[dict[str, str]] = None, value_rules: Optional[dict] = None
) -> dict:
    canonical_rows = extract_canonical_rows(df, OrderDataSource(source), mapping, value_rules)
    quality = compute_ecommerce_quality_report(canonical_rows)

    async with async_session() as db:
        write_result = await write_canonical_rows(db, canonical_rows, uuid.UUID(merchant_id), OrderDataSource(source))

        warnings = list(quality["warnings"])
        defaulted_count = write_result["return_cost_defaulted_count"]
        if defaulted_count > 0:
            warnings.append(
                {
                    "field": "return_cost",
                    "severity": "medium",
                    "message": (
                        f"Return cost is missing for {defaulted_count} of {write_result['items_created']} "
                        "line items (no SKU-level override and no merchant default set). Defaulting to 0 "
                        "for those — net margin may be overstated."
                    ),
                    "features_disabled": [],
                }
            )
        # 3.6: "include duplicate ... counts and reasons in the quality
        # report" -- previously `duplicates_skipped` was only a top-level
        # count on the write result, with no named warning explaining why
        # fewer orders landed than rows were parsed.
        duplicates_skipped = write_result["duplicates_skipped"]
        if duplicates_skipped > 0:
            warnings.append(
                {
                    "field": "external_order_id",
                    "severity": "low",
                    "message": (
                        f"{duplicates_skipped} of {quality['rows_parsed']} parsed row(s) matched an order "
                        "already ingested for this merchant and source (same real or generated order id) "
                        "and were skipped."
                    ),
                    "features_disabled": [],
                }
            )
        quality = {**quality, "duplicates_skipped": duplicates_skipped}

        upload_uuid = uuid.UUID(upload_id)
        upload = (await db.execute(select(Upload).where(Upload.id == upload_uuid))).scalar_one_or_none()
        if upload is None:
            upload = Upload(id=upload_uuid, merchant_id=uuid.UUID(merchant_id), analyzer_type=AnalyzerType.ecommerce)
            db.add(upload)
        upload.data_source = source
        upload.status = UploadStatus.ready
        upload.rows_parsed = quality["rows_parsed"]
        upload.rows_rejected = quality["rows_rejected"]
        upload.date_range_start = quality["date_range_start"]
        upload.date_range_end = quality["date_range_end"]
        upload.days_of_history = quality["days_of_history"]
        upload.warnings = warnings
        upload.analyzer_metadata = {
            **(upload.analyzer_metadata or {}),
            "rejected_rows": quality["rejected_rows"],
            **({"mapping_applied": summarize_mapping_applied(mapping, None, value_rules)} if mapping else {}),
        }
        await db.commit()

    return {**write_result, "quality_report": {**quality, "warnings": warnings}}
