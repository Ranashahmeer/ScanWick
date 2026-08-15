from decimal import Decimal
from typing import Optional


def compute_net_margin(
    *,
    gross_revenue: Decimal,
    refund_amount: Optional[Decimal] = None,
    discount_amount: Optional[Decimal] = None,
    cogs: Optional[Decimal] = None,
    shipping_cost: Optional[Decimal] = None,
    processing_fees: Optional[Decimal] = None,
    allocated_ad_spend: Optional[Decimal] = None,
    return_cost: Optional[Decimal] = None,
) -> Optional[Decimal]:
    """Net margin per spec:
    gross_revenue - refund_amount - discount_amount - cogs - shipping_cost
    - processing_fees - allocated_ad_spend - return_cost.

    Returns None if cogs is unknown. Spec is explicit that gross revenue must
    never be used as a profitability proxy — silently treating unknown COGS
    as 0 would overstate margin, which is exactly that failure mode. Every
    other component defaults to 0 when missing, since those are a real,
    known absence of that cost (no refund happened), not an unknown.
    """
    if cogs is None:
        return None

    return (
        gross_revenue
        - (refund_amount or 0)
        - (discount_amount or 0)
        - cogs
        - (shipping_cost or 0)
        - (processing_fees or 0)
        - (allocated_ad_spend or 0)
        - (return_cost or 0)
    )


def resolve_unit_return_cost(
    sku_override: Optional[Decimal], merchant_default: Optional[Decimal]
) -> tuple[Decimal, bool]:
    """Three-branch fallback per spec: SKU override -> merchant default -> 0.

    Returns (value, defaulted_to_zero) so callers can surface a warning that
    return cost data is missing when neither was set, instead of silently
    treating the resulting 0 as a real measured cost.
    """
    if sku_override is not None:
        return sku_override, False
    if merchant_default is not None:
        return merchant_default, False
    return 0, True
