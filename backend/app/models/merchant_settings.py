import uuid

from sqlalchemy import Column, DateTime, Numeric, String, Uuid
from sqlalchemy.sql import func

from app.models.auth import Base


class MerchantSettings(Base):
    """One row per merchant — global config shared across verticals
    (e-commerce return cost default and the account owner's contact
    email used by automated reports)."""

    __tablename__ = "merchant_settings"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id = Column(Uuid, nullable=False, unique=True, index=True)
    owner_email = Column(String, nullable=True)
    base_currency = Column(String(3), nullable=True)
    default_return_cost = Column(Numeric(14, 4), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
