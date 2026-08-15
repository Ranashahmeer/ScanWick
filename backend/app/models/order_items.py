import uuid

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Uuid

from app.models.auth import Base


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    order_id = Column(Uuid, ForeignKey("orders.id"), nullable=False, index=True)
    merchant_id = Column(Uuid, nullable=False, index=True)
    sku = Column(String, nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Integer, nullable=False)
    unit_cogs = Column(Integer, nullable=True)
    unit_shipping_cost = Column(Integer, nullable=True)
    unit_return_cost = Column(Integer, nullable=True)
    unit_net_margin = Column(Integer, nullable=True)
