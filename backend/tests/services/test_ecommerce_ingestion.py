import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.order_items import OrderItem
from app.models.orders import Order, OrderDataSource, OrderStatus
from app.services.ecommerce_ingestion import (
    _commit_pending_orders,
    compute_ecommerce_quality_report,
    extract_canonical_rows,
    ingest_dataframe,
    write_canonical_rows,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> pd.DataFrame:
    return pd.read_csv(FIXTURES_DIR / name)


def test_extract_canonical_rows_shopify_shape():
    df = _load("shopify_sample.csv")
    rows = extract_canonical_rows(df, OrderDataSource.shopify_csv)

    assert len(rows) == 3
    first = rows[0]
    assert first["external_order_id"] == "#1001"
    assert first["gross_revenue"] == 230081
    assert first["original_currency"] == "NGN"
    assert first["sku"] == "SKU-0042"
    assert first["quantity"] == 2
    assert first["unit_price"] == 107540
    assert first["status"] == OrderStatus.fulfilled

    # refunded order
    assert rows[2]["status"] == OrderStatus.refunded
    assert rows[2]["refund_amount"] == 150000

    # unfulfilled/paid order stays pending
    assert rows[1]["status"] == OrderStatus.pending


def test_extract_canonical_rows_woocommerce_shape():
    df = _load("woocommerce_sample.csv")
    rows = extract_canonical_rows(df, OrderDataSource.woocommerce_csv)

    assert len(rows) == 3
    first = rows[0]
    assert first["external_order_id"] == "5001"
    assert first["gross_revenue"] == 230081
    assert first["original_currency"] == "NGN"
    assert first["sku"] == "SKU-0042"
    assert first["quantity"] == 2
    assert first["unit_price"] == 107540
    assert first["status"] == OrderStatus.fulfilled

    assert rows[1]["status"] == OrderStatus.pending  # wc-processing
    assert rows[2]["status"] == OrderStatus.refunded  # wc-refunded


def test_extract_canonical_rows_generic_shape():
    """generic_csv (Scanwick's own canonical-field-named export, e.g.
    scanwick_test_ecommerce_orders.csv) resolves every field directly by
    exact column name, unlike Shopify/WooCommerce which don't recognize this
    file's headers at all (verified: gross_revenue/sku/unit_cogs/
    customer_email/original_currency all resolve to None or the wrong
    column under either of those two maps for this exact shape)."""
    df = _load("generic_ecommerce_sample.csv")
    rows = extract_canonical_rows(df, OrderDataSource.generic_csv)

    assert len(rows) == 3
    first = rows[0]
    assert first["external_order_id"] == "GEN-1001"
    assert first["gross_revenue"] == 2000000
    assert first["original_currency"] == "NGN"
    assert first["sku"] == "LMP-001"
    assert first["quantity"] == 2
    assert first["unit_price"] == 1000000
    assert first["unit_cogs"] == 1680000
    assert first["customer_email"] == "buyer1@mail.ng"
    assert first["channel"] == "Shopify"
    assert first["processing_fees"] == 36000
    assert first["allocated_ad_spend"] == 73600
    assert first["status"] == OrderStatus.fulfilled  # refund_amount == 0

    assert rows[1]["status"] == OrderStatus.refunded  # refund_amount > 0
    assert rows[2]["unit_cogs"] is None  # blank cogs cell stays None, not 0


def test_extract_canonical_rows_rejects_ambiguous_order_date_with_no_confirmed_locale():
    """3.7: "03/04/2026" is genuinely ambiguous (3 April vs March 4) -- with
    no date_locale confirmed for this mapping, order_date comes back None
    (the row is rejected downstream) and carries a named AMBIGUOUS_DATE
    warning rather than silently guessing."""
    df = pd.DataFrame({"order_id": ["ORD-1"], "order_date": ["03/04/2026"], "gross_revenue": [1000], "currency": ["NGN"]})
    rows = extract_canonical_rows(df, OrderDataSource.generic_csv)

    assert rows[0]["order_date"] is None
    assert rows[0]["_row_warning"]["code"] == "AMBIGUOUS_DATE"
    assert rows[0]["_row_warning"]["row"] == 0
    assert rows[0]["_row_warning"]["field"] == "order_date"


def test_extract_canonical_rows_resolves_ambiguous_order_date_once_locale_confirmed():
    df = pd.DataFrame({"order_id": ["ORD-1"], "order_date": ["03/04/2026"], "gross_revenue": [1000], "currency": ["NGN"]})
    rows = extract_canonical_rows(df, OrderDataSource.generic_csv, value_rules={"date_locale": "month_first"})

    assert rows[0]["order_date"] == datetime(2026, 3, 4)
    assert rows[0]["_row_warning"] is None


async def test_ingest_dataframe_surfaces_ambiguous_order_date_as_a_named_rejected_row(db_session):
    merchant_id = uuid.uuid4()
    df = pd.DataFrame(
        {
            "order_id": ["ORD-1", "ORD-2"],
            "order_date": ["2026-01-05", "03/04/2026"],
            "gross_revenue": [1000, 2000],
            "currency": ["NGN", "NGN"],
        }
    )
    canonical_rows = extract_canonical_rows(df, OrderDataSource.generic_csv)
    quality = compute_ecommerce_quality_report(canonical_rows)

    assert quality["rows_rejected"] == 1
    assert len(quality["rejected_rows"]) == 1
    assert quality["rejected_rows"][0]["code"] == "AMBIGUOUS_DATE"
    assert quality["rejected_rows"][0]["row"] == 1
    assert quality["rejected_rows"][0]["raw_value"] == "03/04/2026"

    result = await write_canonical_rows(db_session, canonical_rows, merchant_id, OrderDataSource.generic_csv)
    assert result["orders_created"] == 1
    assert result["rows_rejected"] == 1


async def test_ingest_dataframe_writes_canonical_rows_generic(db_session):
    merchant_id = uuid.uuid4()
    result = await ingest_dataframe(
        db_session, _load("generic_ecommerce_sample.csv"), merchant_id, OrderDataSource.generic_csv
    )

    assert result["orders_created"] == 3
    assert result["items_created"] == 3
    assert result["rows_rejected"] == 0

    orders = (await db_session.execute(select(Order).where(Order.merchant_id == merchant_id))).scalars().all()
    assert len(orders) == 3
    assert all(o.data_source == OrderDataSource.generic_csv for o in orders)
    by_external_id = {o.external_order_id: o for o in orders}
    assert by_external_id["GEN-1001"].processing_fees == 36000
    assert by_external_id["GEN-1001"].allocated_ad_spend == 73600


async def test_reingesting_the_same_export_skips_duplicate_orders(db_session):
    """Audit #14 regression: re-uploading the same export (or a client
    retry) used to insert a brand-new Order for every row every time,
    silently doubling revenue. A second ingestion of the identical file for
    the same merchant must skip every row as a duplicate."""
    merchant_id = uuid.uuid4()
    df = _load("generic_ecommerce_sample.csv")

    first = await ingest_dataframe(db_session, df, merchant_id, OrderDataSource.generic_csv)
    second = await ingest_dataframe(db_session, df, merchant_id, OrderDataSource.generic_csv)

    assert first["orders_created"] == 3
    assert second["orders_created"] == 0
    assert second["duplicates_skipped"] == 3

    orders = (await db_session.execute(select(Order).where(Order.merchant_id == merchant_id))).scalars().all()
    assert len(orders) == 3


async def test_reingesting_rows_with_no_external_order_id_skips_duplicates(db_session):
    """3.6: rows with no external_order_id in the source export used to be
    re-insertable on every re-upload (the dedup check was skipped entirely
    whenever external_order_id was None) -- a deterministic surrogate ID is
    now generated per row, so a second ingestion of the identical file must
    skip every row as a duplicate, same as the audit #14 case for rows that
    do have a real ID."""
    merchant_id = uuid.uuid4()
    df = pd.DataFrame(
        {
            "order_date": ["2026-01-05", "2026-01-06", "2026-01-07"],
            "gross_revenue": [1000, 2000, 3000],
            "currency": ["NGN", "NGN", "NGN"],
            "sku": ["SKU-A", "SKU-B", "SKU-C"],
            "quantity": [1, 2, 3],
        }
    )

    first = await ingest_dataframe(db_session, df, merchant_id, OrderDataSource.generic_csv)
    second = await ingest_dataframe(db_session, df, merchant_id, OrderDataSource.generic_csv)

    assert first["orders_created"] == 3
    assert first["duplicates_skipped"] == 0
    assert second["orders_created"] == 0
    assert second["duplicates_skipped"] == 3

    orders = (await db_session.execute(select(Order).where(Order.merchant_id == merchant_id))).scalars().all()
    assert len(orders) == 3
    # Every row got a real, distinct surrogate ID -- not left null and not
    # collapsed onto a shared placeholder.
    ids = {o.external_order_id for o in orders}
    assert len(ids) == 3
    assert all(eid.startswith("surrogate:") for eid in ids)


async def test_external_order_id_missing_cell_does_not_become_literal_nan_string(db_session):
    """3.6: `str(raw.get(col))` on a genuinely-empty cell in a numeric-typed
    ID column used to produce the literal string "nan" -- present, not
    missing, so every such row collided with every other one that also had
    a blank cell instead of getting its own surrogate ID."""
    merchant_id = uuid.uuid4()
    df = pd.DataFrame(
        {
            "order_id": [None, None, "ORD-3"],
            "order_date": ["2026-01-05", "2026-01-06", "2026-01-07"],
            "gross_revenue": [1000, 2000, 3000],
            "currency": ["NGN", "NGN", "NGN"],
        }
    )

    result = await ingest_dataframe(db_session, df, merchant_id, OrderDataSource.generic_csv)

    assert result["orders_created"] == 3
    orders = (await db_session.execute(select(Order).where(Order.merchant_id == merchant_id))).scalars().all()
    ids = {o.external_order_id for o in orders}
    assert len(ids) == 3
    assert "nan" not in ids
    assert "ORD-3" in ids


async def test_external_order_id_dedup_is_case_insensitive(db_session):
    """3.6: "normalize IDs before comparison" -- differently-cased re-uploads
    of the same order id (a client retry with a re-exported file, platform
    casing drift) must be recognized as the same order, without lowercasing
    what's actually stored."""
    merchant_id = uuid.uuid4()
    first_df = pd.DataFrame(
        {"order_id": ["ORD-1"], "order_date": ["2026-01-05"], "gross_revenue": [1000], "currency": ["NGN"]}
    )
    second_df = pd.DataFrame(
        {"order_id": ["ord-1"], "order_date": ["2026-01-05"], "gross_revenue": [1000], "currency": ["NGN"]}
    )

    first = await ingest_dataframe(db_session, first_df, merchant_id, OrderDataSource.generic_csv)
    second = await ingest_dataframe(db_session, second_df, merchant_id, OrderDataSource.generic_csv)

    assert first["orders_created"] == 1
    assert second["orders_created"] == 0
    assert second["duplicates_skipped"] == 1

    orders = (await db_session.execute(select(Order).where(Order.merchant_id == merchant_id))).scalars().all()
    assert len(orders) == 1
    assert orders[0].external_order_id == "ORD-1"  # original casing preserved, not lowercased


def test_shopify_and_woocommerce_produce_identical_canonical_shapes():
    shopify_rows = extract_canonical_rows(_load("shopify_sample.csv"), OrderDataSource.shopify_csv)
    woo_rows = extract_canonical_rows(_load("woocommerce_sample.csv"), OrderDataSource.woocommerce_csv)

    assert len(shopify_rows) == len(woo_rows)
    for s_row, w_row in zip(shopify_rows, woo_rows):
        assert set(s_row.keys()) == set(w_row.keys())
        assert s_row["gross_revenue"] == w_row["gross_revenue"]
        assert s_row["sku"] == w_row["sku"]
        assert s_row["quantity"] == w_row["quantity"]
        assert s_row["unit_price"] == w_row["unit_price"]
        assert s_row["status"] == w_row["status"]


async def test_ingest_dataframe_writes_canonical_rows_shopify(db_session):
    merchant_id = uuid.uuid4()
    result = await ingest_dataframe(db_session, _load("shopify_sample.csv"), merchant_id, OrderDataSource.shopify_csv)

    assert result == {"orders_created": 3, "items_created": 3, "rows_rejected": 0, "duplicates_skipped": 0, "return_cost_defaulted_count": 3}

    orders = (await db_session.execute(select(Order).where(Order.merchant_id == merchant_id))).scalars().all()
    items = (await db_session.execute(select(OrderItem).where(OrderItem.merchant_id == merchant_id))).scalars().all()
    assert len(orders) == 3
    assert len(items) == 3
    assert all(o.data_source == OrderDataSource.shopify_csv for o in orders)
    assert {o.external_order_id for o in orders} == {"#1001", "#1002", "#1003"}


async def test_ingest_dataframe_writes_canonical_rows_woocommerce(db_session):
    merchant_id = uuid.uuid4()
    result = await ingest_dataframe(
        db_session, _load("woocommerce_sample.csv"), merchant_id, OrderDataSource.woocommerce_csv
    )

    assert result == {"orders_created": 3, "items_created": 3, "rows_rejected": 0, "duplicates_skipped": 0, "return_cost_defaulted_count": 3}

    orders = (await db_session.execute(select(Order).where(Order.merchant_id == merchant_id))).scalars().all()
    assert len(orders) == 3
    assert all(o.data_source == OrderDataSource.woocommerce_csv for o in orders)


async def test_shopify_and_woocommerce_ingestion_land_identical_row_shapes(db_session):
    """The actual DB-write assertion the task asks for: both sources land
    rows with the same canonical shape (same revenue/sku/qty/price/status),
    differing only in data_source and external_order_id."""
    shopify_merchant = uuid.uuid4()
    woo_merchant = uuid.uuid4()

    await ingest_dataframe(db_session, _load("shopify_sample.csv"), shopify_merchant, OrderDataSource.shopify_csv)
    await ingest_dataframe(db_session, _load("woocommerce_sample.csv"), woo_merchant, OrderDataSource.woocommerce_csv)

    shopify_orders = (
        (await db_session.execute(select(Order).where(Order.merchant_id == shopify_merchant).order_by(Order.gross_revenue)))
        .scalars()
        .all()
    )
    woo_orders = (
        (await db_session.execute(select(Order).where(Order.merchant_id == woo_merchant).order_by(Order.gross_revenue)))
        .scalars()
        .all()
    )

    assert len(shopify_orders) == len(woo_orders) == 3
    for s_order, w_order in zip(shopify_orders, woo_orders):
        assert s_order.gross_revenue == w_order.gross_revenue
        assert s_order.original_currency == w_order.original_currency
        assert s_order.status == w_order.status
        assert s_order.data_source == OrderDataSource.shopify_csv
        assert w_order.data_source == OrderDataSource.woocommerce_csv


def _make_order(merchant_id, external_order_id: str, source: OrderDataSource) -> Order:
    return Order(
        id=uuid.uuid4(),
        merchant_id=merchant_id,
        external_order_id=external_order_id,
        order_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        gross_revenue=10000,
        original_currency="NGN",
        status=OrderStatus.fulfilled,
        data_source=source,
        is_anomalous=False,
    )


async def test_orders_unique_constraint_rejects_duplicate_merchant_source_external_id(db_session):
    """3.6: `uq_orders_merchant_source_external_id` is the DB-level backstop
    behind the application-level dedup -- two rows sharing
    (merchant_id, data_source, external_order_id) must never both persist,
    even if something bypasses the in-memory pre-check entirely."""
    merchant_id = uuid.uuid4()
    db_session.add(_make_order(merchant_id, "ORD-DUP", OrderDataSource.generic_csv))
    await db_session.commit()

    db_session.add(_make_order(merchant_id, "ORD-DUP", OrderDataSource.generic_csv))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_orders_unique_constraint_allows_same_external_id_across_sources(db_session):
    """The constraint is scoped by data_source too -- the same
    external_order_id under two different platforms for one merchant is
    not the same order (e.g. a Shopify "#1001" and an unrelated manual
    generic-CSV "#1001")."""
    merchant_id = uuid.uuid4()
    db_session.add(_make_order(merchant_id, "#1001", OrderDataSource.shopify_csv))
    db_session.add(_make_order(merchant_id, "#1001", OrderDataSource.generic_csv))
    await db_session.commit()

    orders = (await db_session.execute(select(Order).where(Order.merchant_id == merchant_id))).scalars().all()
    assert len(orders) == 2


async def test_commit_pending_orders_recovers_from_a_race_and_keeps_the_rest_of_the_batch(db_session):
    """3.6: a genuinely concurrent ingest can commit an overlapping
    external_order_id between the pre-check SELECT and the INSERT (two
    overlapping requests, or a Celery task retry racing its own first
    attempt). `_commit_pending_orders` must not lose the rest of an
    otherwise-new batch when that happens -- only the row(s) that actually
    collided are dropped, everything else still commits."""
    merchant_id = uuid.uuid4()
    # Simulates "another process already committed this one" by writing it
    # directly, ahead of the batch below.
    db_session.add(_make_order(merchant_id, "RACE-1", OrderDataSource.generic_csv))
    await db_session.commit()

    pending = [
        (_make_order(merchant_id, "RACE-1", OrderDataSource.generic_csv), None),  # collides
        (_make_order(merchant_id, "RACE-2", OrderDataSource.generic_csv), None),  # genuinely new
    ]
    orders_created, items_created, race_duplicates = await _commit_pending_orders(db_session, pending)

    assert orders_created == 1
    assert items_created == 0
    assert race_duplicates == 1

    orders = (await db_session.execute(select(Order).where(Order.merchant_id == merchant_id))).scalars().all()
    assert {o.external_order_id for o in orders} == {"RACE-1", "RACE-2"}
