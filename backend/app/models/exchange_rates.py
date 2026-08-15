import uuid

from sqlalchemy import Column, Date, Numeric, String, UniqueConstraint, Uuid

from app.models.auth import Base


class ExchangeRate(Base):
    """Historical FX rate store. Not a table in the spec — no FX data
    provider is named anywhere in the Developer Guide despite "convert at
    order_date rate" being a hard requirement on every analyzer. This is the
    minimal seam: a (quote_currency, base_currency, rate_date) -> rate
    lookup. Populating it from a real FX provider is a follow-on; for now
    rows are seeded directly (e.g. in tests) or will need a sync job."""

    __tablename__ = "exchange_rates"
    __table_args__ = (UniqueConstraint("quote_currency", "base_currency", "rate_date"),)

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    quote_currency = Column(String(3), nullable=False, index=True)
    base_currency = Column(String(3), nullable=False, index=True)
    rate_date = Column(Date, nullable=False, index=True)
    rate = Column(Numeric(10, 6), nullable=False)
