def test_webhook_paystack_rejects_bad_signature(sync_client):
    response = sync_client.post(
        "/api/v1/webhooks/paystack",
        json={"event": "charge.success", "data": {}},
        headers={"x-paystack-signature": "not-a-real-signature"},
    )
    assert response.status_code == 401


def test_webhook_flutterwave_rejects_bad_signature(sync_client):
    response = sync_client.post(
        "/api/v1/webhooks/flutterwave",
        json={"event": "charge.completed", "data": {}},
        headers={"verif-hash": "not-the-configured-secret"},
    )
    assert response.status_code == 401
