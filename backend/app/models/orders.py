import uuid
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Numeric, String, UniqueConstraint, Uuid, Integer
from sqlalchemy import Enum as SAEnum

from app.models.auth import Base


class OrderStatus(str, Enum):
    pending = "pending"
    fulfilled = "fulfilled"
    refunded = "refunded"
    cancelled = "cancelled"


class OrderDataSource(str, Enum):
    shopify_csv = "shopify_csv"
    woocommerce_csv = "woocommerce_csv"
    shopify_api = "shopify_api"
    # Scanwick's own canonical-field-named CSV export (column names matching
    # this model's own fields directly, e.g. scanwick_test_ecommerce_orders.csv)
    # -- distinct from a specific e-commerce platform's export format.
    generic_csv = "generic_csv"


class Order(Base):
    """Canonical e-commerce order row, written by the ingestion pipeline (step
    1.10). Separate from whatever in-memory dataframe the existing /api/analyze
    CSV analyzer uses today — see docs for how the two coexist."""

    __tablename__ = "orders"
    __table_args__ = (
        # 3.6: rows with no real external_order_id used to be re-insertable
        # on every re-upload -- ingestion now always supplies a real or a
        # deterministic surrogate ID (see ecommerce_ingestion.py's
        # `_generate_surrogate_external_id`), and this constraint is the DB-
        # level backstop for that in-memory dedup, catching a genuinely
        # concurrent ingest that races between the pre-check SELECT and the
        # INSERT. Scoped by data_source too: the same external_order_id
        # under two different platforms for one merchant is not the same
        # order.
        UniqueConstraint(
            "merchant_id", "data_source", "external_order_id", name="uq_orders_merchant_source_external_id"
        ),
    )

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id = Column(Uuid, nullable=False, index=True)
    external_order_id = Column(String, nullable=True)
    order_date = Column(DateTime(timezone=True), nullable=False)
    gross_revenue = Column(Integer, nullable=False)
    original_currency = Column(String(3), nullable=False)
    base_currency_amount = Column(Integer, nullable=True)
    exchange_rate_at_order = Column(Numeric(10, 6), nullable=True)
    refund_amount = Column(Integer, nullable=True)
    discount_amount = Column(Integer, nullable=True)
    shipping_cost = Column(Integer, nullable=True)
    processing_fees = Column(Integer, nullable=True)
    allocated_ad_spend = Column(Integer, nullable=True)
    cogs = Column(Integer, nullable=True)
    net_margin = Column(Integer, nullable=True)
    channel = Column(String, nullable=True)
    customer_id = Column(Uuid, nullable=True, index=True)
    status = Column(SAEnum(OrderStatus), nullable=False)
    data_source = Column(SAEnum(OrderDataSource), nullable=False)
    is_anomalous = Column(Boolean, nullable=False, default=False)
