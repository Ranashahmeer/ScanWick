def test_subscription_defaults_to_free_for_a_user_with_no_subscription_row(authenticated_client):
    response = authenticated_client.get("/api/v1/payments/subscription")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["tier"] == "free"
    assert body["data"]["status"] is None


def test_history_is_empty_for_a_user_with_no_transactions(authenticated_client):
    response = authenticated_client.get("/api/v1/payments/history")

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_checkout_returns_502_when_neither_provider_is_configured(authenticated_client):
    # Neither PAYSTACK_SECRET_KEY nor FLUTTERWAVE_SECRET_KEY is set in the
    # test environment, so both providers fail — proves the route surfaces
    # a real error instead of a bare 500 when the fallback itself fails.
    response = authenticated_client.post("/api/v1/payments/checkout", json={"tier": "premium"})

    assert response.status_code == 502
    assert response.json()["success"] is False


def test_checkout_rejects_free_tier(authenticated_client):
    response = authenticated_client.post("/api/v1/payments/checkout", json={"tier": "free"})

    assert response.status_code == 422
