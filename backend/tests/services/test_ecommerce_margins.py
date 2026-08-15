from decimal import Decimal

import pytest

from app.services.ecommerce_margins import compute_net_margin, resolve_unit_return_cost


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        # All components present.
        (
            dict(
                gross_revenue=230081,
                refund_amount=0,
                discount_amount=0,
                cogs=90000,
                shipping_cost=15000,
                processing_fees=3000,
                allocated_ad_spend=8000,
                return_cost=5000,
            ),
            109081,
        ),
        # Missing optional components default to 0, not None-propagation.
        (dict(gross_revenue=100000, cogs=40000), 60000),
        # Refunds/discounts/return cost can push margin negative.
        (
            dict(
                gross_revenue=32000000,
                refund_amount=4200000,
                discount_amount=3800000,
                cogs=18180000,
                shipping_cost=6700000,
                allocated_ad_spend=18180000,
            ),
            -19060000,
        ),
    ],
)
def test_compute_net_margin_matches_formula(kwargs, expected):
    assert compute_net_margin(**kwargs) == expected


def test_compute_net_margin_returns_none_when_cogs_unknown():
    """Gross revenue must never be used as a profitability proxy — an
    unknown COGS must not silently become a 0 that overstates margin."""
    result = compute_net_margin(gross_revenue=100000, cogs=None)
    assert result is None


def test_compute_net_margin_zero_cogs_is_not_the_same_as_unknown_cogs():
    """0 is a real, known cogs value — distinct from None."""
    result = compute_net_margin(gross_revenue=100000, cogs=0)
    assert result == 100000


@pytest.mark.parametrize(
    "sku_override,merchant_default,expected_value,expected_defaulted",
    [
        # Branch 1: SKU-level override present — always wins, even over a merchant default.
        (7500, 5000, 7500, False),
        (7500, None, 7500, False),
        # Branch 2: no SKU override, falls back to merchant default.
        (None, 5000, 5000, False),
        # Branch 3: neither set — defaults to 0 and flags it.
        (None, None, 0, True),
    ],
)
def test_resolve_unit_return_cost_fallback_branches(sku_override, merchant_default, expected_value, expected_defaulted):
    value, defaulted = resolve_unit_return_cost(sku_override, merchant_default)
    assert value == expected_value
    assert defaulted is expected_defaulted


def test_resolve_unit_return_cost_sku_override_of_zero_is_respected_not_treated_as_missing():
    """An explicit SKU override of exactly 0 is a real value (e.g. free
    returns for this SKU), not the same as 'not set'."""
    value, defaulted = resolve_unit_return_cost(0, 5000)
    assert value == 0
    assert defaulted is False
