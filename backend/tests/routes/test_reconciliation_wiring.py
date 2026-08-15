"""Task 5.5: for one run per analyzer, the reconciliation record's
records_analyzed/excluded counts must match the actual underlying data —
not just exist. Each test calls a real endpoint (through `client`, which
bypasses RBAC for this kind of business-logic test), reads back the
analysis_run_id it returns via GET /api/v1/reconciliation/{id}, and
verifies the persisted counts against the real fixture data."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from app.models.accounts import Account
from app.models.bank_transactions import BankTransaction, BankTransactionDataSource, TransactionType
from app.models.orders import Order, OrderDataSource, OrderStatus


async def test_ecommerce_reconciliation_record_matches_actual_order_counts(client, db_session):
    merchant_id = uuid.uuid4()
    eligible_orders = [
        Order(
            id=uuid.uuid4(), merchant_id=merchant_id, order_date=datetime(2026, 1, 15, tzinfo=timezone.utc),
            gross_revenue=10000000, original_currency="NGN", status=OrderStatus.fulfilled,
            data_source=OrderDataSource.shopify_csv, is_anomalous=False,
        )
        for _ in range(3)
    ]
    anomalous_order = Order(
        id=uuid.uuid4(), merchant_id=merchant_id, order_date=datetime(2026, 1, 16, tzinfo=timezone.utc),
        gross_revenue=9999999900, original_currency="NGN", status=OrderStatus.fulfilled,
        data_source=OrderDataSource.shopify_csv, is_anomalous=True,
    )
    db_session.add_all(eligible_orders + [anomalous_order])
    await db_session.commit()

    response = await client.get(f"/api/v1/ecommerce/dashboard/summary?merchant_id={merchant_id}")
    assert response.status_code == 200
    analysis_run_id = response.json()["meta"]["analysis_run_id"]
    assert analysis_run_id is not None

    reconciliation_response = await client.get(f"/api/v1/reconciliation/{analysis_run_id}")
    assert reconciliation_response.status_code == 200
    reconciliation = reconciliation_response.json()["data"]
    assert reconciliation["analyzer_type"] == "ecommerce"
    assert reconciliation["records_analyzed"] == 3  # only the 3 eligible (non-anomalous) orders


async def test_bank_reconciliation_record_matches_actual_transaction_counts(client, db_session):
    account = Account(id=uuid.uuid4(), user_id=uuid.uuid4(), account_number_hash="r" * 64, bank_name="GTBank")
    db_session.add(account)
    await db_session.commit()

    eligible_transactions_list = [
        BankTransaction(
            id=uuid.uuid4(), account_id=account.id, transaction_date=datetime(2026, 1, 1).date(),
            amount=int(float(f"-{1000 + i}") * 100), original_currency="NGN", type=TransactionType.debit,
            payee_normalized=f"Vendor {i}", data_source=BankTransactionDataSource.generic_csv,
        )
        for i in range(5)
    ]
    own_account_transfer = BankTransaction(
        id=uuid.uuid4(), account_id=account.id, transaction_date=datetime(2026, 1, 2).date(),
        amount=-50000000, original_currency="NGN", type=TransactionType.debit,
        payee_normalized="My Savings", data_source=BankTransactionDataSource.generic_csv,
        is_own_account_transfer=True,
    )
    db_session.add_all(eligible_transactions_list + [own_account_transfer])
    await db_session.commit()

    response = await client.get(f"/api/v1/bank/dashboard/summary?account_id={account.id}")
    assert response.status_code == 200
    analysis_run_id = response.json()["meta"]["analysis_run_id"]
    assert analysis_run_id is not None

    reconciliation_response = await client.get(f"/api/v1/reconciliation/{analysis_run_id}")
    assert reconciliation_response.status_code == 200
    reconciliation = reconciliation_response.json()["data"]
    assert reconciliation["analyzer_type"] == "bank"
    assert reconciliation["records_analyzed"] == 5  # the 5 eligible transactions
    assert reconciliation["records_excluded"] == 1  # the 1 own-account-transfer
