import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models import PaymentTransaction, User
from app.services import payments
from app.services.payment_provider import CheckoutResult
from app.services.paystack_client import PaystackAPIError


async def _make_user(db_session) -> User:
    user = User(email="owner@example.com", first_name="Ada", last_name="Owner", is_verified=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def test_initiate_checkout_uses_paystack_by_default(db_session):
    user = await _make_user(db_session)

    with patch.object(
        payments._PRIMARY,
        "initialize_transaction",
        new=AsyncMock(return_value=CheckoutResult(authorization_url="https://paystack.test/pay", reference="ref-1")),
    ):
        result = await payments.initiate_checkout(db_session, user, "premium")

    assert result.reference == "ref-1"
    transaction = (
        await db_session.execute(select(PaymentTransaction).where(PaymentTransaction.provider_reference == "ref-1"))
    ).scalar_one()
    assert transaction.provider == "paystack"
    assert transaction.user_id == user.id


async def test_initiate_checkout_falls_back_to_flutterwave_when_paystack_fails(db_session):
    """The core of the "second, fallback layer" behavior: a Paystack API
    error must not fail the checkout outright — it transparently retries
    through Flutterwave instead."""
    user = await _make_user(db_session)

    with (
        patch.object(
            payments._PRIMARY, "initialize_transaction", new=AsyncMock(side_effect=PaystackAPIError("down"))
        ),
        patch.object(
            payments._FALLBACK,
            "initialize_transaction",
            new=AsyncMock(
                return_value=CheckoutResult(authorization_url="https://flutterwave.test/pay", reference="ref-2")
            ),
        ),
    ):
        result = await payments.initiate_checkout(db_session, user, "premium")

    assert result.authorization_url == "https://flutterwave.test/pay"
    transaction = (
        await db_session.execute(select(PaymentTransaction).where(PaymentTransaction.provider_reference == "ref-2"))
    ).scalar_one()
    assert transaction.provider == "flutterwave"


async def test_initiate_checkout_accepts_basic_tier_too(db_session):
    """Basic is a real, separately-paid tier — not just a synonym for the
    free default — so it must be checkout-able exactly like premium."""
    user = await _make_user(db_session)

    with patch.object(
        payments._PRIMARY,
        "initialize_transaction",
        new=AsyncMock(return_value=CheckoutResult(authorization_url="https://paystack.test/pay", reference="ref-3")),
    ):
        result = await payments.initiate_checkout(db_session, user, "basic")

    assert result.reference == "ref-3"
    transaction = (
        await db_session.execute(select(PaymentTransaction).where(PaymentTransaction.provider_reference == "ref-3"))
    ).scalar_one()
    assert transaction.tier == "basic"


async def test_initiate_checkout_rejects_free_tier(db_session):
    """Free needs no checkout at all — it's the unpaid default, not
    something to charge a card for."""
    user = await _make_user(db_session)

    with pytest.raises(ValueError):
        await payments.initiate_checkout(db_session, user, "free")


async def test_checkout_amount_is_the_fixed_usd_price_converted_at_the_live_rate(db_session):
    """The whole point of the fx_rates integration: the NGN amount actually
    charged is the fixed USD price (config.py) times the live rate — never
    a hardcoded NGN figure. conftest.py's autouse fixture fixes the test
    rate at 1500.00, so premium's $16.99 must charge exactly ₦25,485.00."""
    user = await _make_user(db_session)

    with patch.object(
        payments._PRIMARY,
        "initialize_transaction",
        new=AsyncMock(return_value=CheckoutResult(authorization_url="https://paystack.test/pay", reference="ref-4")),
    ):
        await payments.initiate_checkout(db_session, user, "premium")

    transaction = (
        await db_session.execute(select(PaymentTransaction).where(PaymentTransaction.provider_reference == "ref-4"))
    ).scalar_one()
    assert transaction.amount == 2548500
    assert transaction.currency == "NGN"
