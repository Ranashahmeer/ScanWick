import json
import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.models.accounts import Account
from app.models.bank_transactions import BankTransaction, BankTransactionDataSource, TransactionType


async def _make_account_with_anomaly(db_session) -> Account:
    account = Account(id=uuid.uuid4(), user_id=uuid.uuid4(), account_number_hash="x" * 64, bank_name="GTBank")
    db_session.add(account)
    await db_session.commit()

    base = date(2026, 1, 1)
    transactions = [
        BankTransaction(
            id=uuid.uuid4(),
            account_id=account.id,
            transaction_date=base + timedelta(days=i),
            amount=int(float(f"-{12000 + i * 137}") * 100),
            original_currency="NGN",
            payee_normalized=f"Vendor {i}",
            type=TransactionType.debit,
            data_source=BankTransactionDataSource.generic_csv,
        )
        for i in range(10)
    ]
    transactions.append(
        BankTransaction(
            id=uuid.uuid4(),
            account_id=account.id,
            transaction_date=base + timedelta(days=20),
            amount=-480000000,
            original_currency="NGN",
            payee_normalized="Suspicious Vendor",
            type=TransactionType.debit,
            data_source=BankTransactionDataSource.generic_csv,
        )
    )
    db_session.add_all(transactions)
    await db_session.commit()
    return account


async def test_get_fraud_risk_found(client, db_session):
    account = await _make_account_with_anomaly(db_session)

    response = await client.get(f"/api/v1/bank/predictive/fraud-risk?account_id={account.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]["flags"]) >= 1
    assert body["data"]["flags"][0]["flag_type"] == "z_score_anomaly"
    assert "score_breakdown" in body["data"]
    assert "statement_integrity" in body["data"]


async def test_get_fraud_risk_excludes_own_account_transfers(client, db_session):
    """Regression test for the standalone-route gap found during the 3.14
    checkpoint: the fraud-risk route only filtered is_anomalous at the DB
    query level, never is_own_account_transfer, even though every other
    Bank predictive endpoint excludes both."""
    account = Account(id=uuid.uuid4(), user_id=uuid.uuid4(), account_number_hash="o" * 64, bank_name="GTBank")
    db_session.add(account)
    await db_session.commit()

    base = date(2026, 1, 1)
    transactions = [
        BankTransaction(
            id=uuid.uuid4(),
            account_id=account.id,
            transaction_date=base + timedelta(days=i),
            amount=int(float(f"-{12000 + i * 137}") * 100),
            original_currency="NGN",
            payee_normalized=f"Vendor {i}",
            type=TransactionType.debit,
            data_source=BankTransactionDataSource.generic_csv,
        )
        for i in range(10)
    ]
    transactions.append(
        BankTransaction(
            id=uuid.uuid4(),
            account_id=account.id,
            transaction_date=base + timedelta(days=20),
            amount=-500000000,
            original_currency="NGN",
            payee_normalized="Own Savings Account",
            type=TransactionType.debit,
            is_own_account_transfer=True,
            data_source=BankTransactionDataSource.generic_csv,
        )
    )
    db_session.add_all(transactions)
    await db_session.commit()

    response = await client.get(f"/api/v1/bank/predictive/fraud-risk?account_id={account.id}")

    assert response.status_code == 200
    body = response.json()
    assert all(flag["flag_type"] != "z_score_anomaly" for flag in body["data"]["flags"])


async def test_get_fraud_risk_not_found(client, db_session):
    response = await client.get(f"/api/v1/bank/predictive/fraud-risk?account_id={uuid.uuid4()}")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "ACCOUNT_NOT_FOUND"


async def test_get_fraud_risk_invalid_account_id(client, db_session):
    response = await client.get("/api/v1/bank/predictive/fraud-risk?account_id=not-a-uuid")

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "INVALID_ACCOUNT_ID"


async def test_get_fraud_risk_requires_account_id(client, db_session):
    response = await client.get("/api/v1/bank/predictive/fraud-risk")
    assert response.status_code == 422


async def test_get_loan_readiness_found(client, db_session):
    account = await _make_account_with_anomaly(db_session)

    response = await client.get(f"/api/v1/bank/predictive/loan-readiness?account_id={account.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "loan_readiness_score" in body["data"]
    assert body["data"]["creditworthiness_tier"] in ("A", "B", "C", "D")
    assert "estimated_debt_coverage_indicator" in body["data"]


async def test_get_loan_readiness_not_found(client, db_session):
    response = await client.get(f"/api/v1/bank/predictive/loan-readiness?account_id={uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"


async def test_get_loan_readiness_invalid_account_id(client, db_session):
    response = await client.get("/api/v1/bank/predictive/loan-readiness?account_id=not-a-uuid")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_ACCOUNT_ID"


async def _make_account_with_net_burn(db_session) -> Account:
    """Real income *and* expenses, with expenses exceeding income — needed
    for the cash-runway test: a debit-only fixture has no income to reduce,
    so the stress scenario couldn't possibly differ from the primary one."""
    account = Account(id=uuid.uuid4(), user_id=uuid.uuid4(), account_number_hash="y" * 64, bank_name="Access Bank")
    db_session.add(account)
    await db_session.commit()

    balance = 500000000
    transactions = []
    for day_base in (1, 32, 63, 94):
        d = date(2026, 1, 1) + timedelta(days=day_base - 1)
        balance += 40000000
        transactions.append(
            BankTransaction(
                id=uuid.uuid4(),
                account_id=account.id,
                transaction_date=d,
                amount=40000000,
                original_currency="NGN",
                balance_after=balance,
                payee_normalized="Salary Inc",
                type=TransactionType.credit,
                data_source=BankTransactionDataSource.generic_csv,
            )
        )
        balance -= 50000000
        transactions.append(
            BankTransaction(
                id=uuid.uuid4(),
                account_id=account.id,
                transaction_date=d + timedelta(days=2),
                amount=-50000000,
                original_currency="NGN",
                balance_after=balance,
                payee_normalized="Landlord Rent",
                type=TransactionType.debit,
                data_source=BankTransactionDataSource.generic_csv,
            )
        )
    db_session.add_all(transactions)
    await db_session.commit()
    return account


async def test_get_cashflow_forecast_found(client, db_session):
    account = await _make_account_with_net_burn(db_session)

    response = await client.get(f"/api/v1/bank/predictive/cashflow-forecast?account_id={account.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["forecast_days"] == 90
    assert len(body["data"]["daily_forecast"]) == 90

    runway = body["data"]["cash_runway"]
    assert runway["stress_scenario_months"] < runway["primary_scenario_months"]

    payees = {c["payee"] for c in body["data"]["recurring_commitments_projected"]}
    assert "Landlord Rent" in payees


async def test_get_cashflow_forecast_not_found(client, db_session):
    response = await client.get(f"/api/v1/bank/predictive/cashflow-forecast?account_id={uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"


async def test_get_cashflow_forecast_invalid_account_id(client, db_session):
    response = await client.get("/api/v1/bank/predictive/cashflow-forecast?account_id=not-a-uuid")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_ACCOUNT_ID"


async def test_get_dashboard_summary_both_exclusion_rules_applied(client, db_session):
    """The task's explicit ask: both is_anomalous and is_own_account_transfer
    exclusions applied to the totals."""
    account = Account(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        account_number_hash="y" * 64,
        bank_name="Access Bank",
        opening_balance=100000000,
        closing_balance=110000000,
    )
    db_session.add(account)
    await db_session.commit()

    transactions = [
        BankTransaction(
            id=uuid.uuid4(),
            account_id=account.id,
            transaction_date=date(2026, 1, 5),
            amount=10000000,
            original_currency="NGN",
            payee_normalized="Client A",
            type=TransactionType.credit,
            data_source=BankTransactionDataSource.generic_csv,
        ),
        BankTransaction(
            id=uuid.uuid4(),
            account_id=account.id,
            transaction_date=date(2026, 1, 10),
            amount=99999999900,
            original_currency="NGN",
            payee_normalized="Anomaly",
            type=TransactionType.credit,
            is_anomalous=True,
            data_source=BankTransactionDataSource.generic_csv,
        ),
        BankTransaction(
            id=uuid.uuid4(),
            account_id=account.id,
            transaction_date=date(2026, 1, 15),
            amount=88888888800,
            original_currency="NGN",
            payee_normalized="Own Account",
            type=TransactionType.credit,
            is_own_account_transfer=True,
            data_source=BankTransactionDataSource.generic_csv,
        ),
    ]
    db_session.add_all(transactions)
    await db_session.commit()

    response = await client.get(f"/api/v1/bank/dashboard/summary?account_id={account.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["inflows"] == 10000000.0


async def test_get_dashboard_summary_not_found(client, db_session):
    response = await client.get(f"/api/v1/bank/dashboard/summary?account_id={uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"


async def test_get_dashboard_summary_invalid_account_id(client, db_session):
    response = await client.get("/api/v1/bank/dashboard/summary?account_id=not-a-uuid")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_ACCOUNT_ID"


async def test_get_income_stability_stable_classification(client, db_session):
    account = Account(id=uuid.uuid4(), user_id=uuid.uuid4(), account_number_hash="z" * 64, bank_name="GTBank")
    db_session.add(account)
    await db_session.commit()

    db_session.add_all(
        [
            BankTransaction(
                id=uuid.uuid4(),
                account_id=account.id,
                transaction_date=date(2026, month, 1),
                amount=int(float(amount) * 100),
                original_currency="NGN",
                type=TransactionType.credit,
                data_source=BankTransactionDataSource.generic_csv,
            )
            for month, amount in zip(range(1, 4), ["100000", "105000", "95000"])
        ]
    )
    await db_session.commit()

    response = await client.get(f"/api/v1/bank/diagnostic/income-stability?account_id={account.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["label"] == "stable"
    assert body["meta"]["disabled_features"] == []


async def test_get_income_stability_disabled_under_3_months(client, db_session):
    account = Account(id=uuid.uuid4(), user_id=uuid.uuid4(), account_number_hash="w" * 64, bank_name="GTBank")
    db_session.add(account)
    await db_session.commit()

    db_session.add_all(
        [
            BankTransaction(
                id=uuid.uuid4(),
                account_id=account.id,
                transaction_date=date(2026, month, 1),
                amount=int(float(amount) * 100),
                original_currency="NGN",
                type=TransactionType.credit,
                data_source=BankTransactionDataSource.generic_csv,
            )
            for month, amount in zip(range(1, 3), ["100000", "105000"])
        ]
    )
    await db_session.commit()

    response = await client.get(f"/api/v1/bank/diagnostic/income-stability?account_id={account.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["data"] is None
    assert len(body["meta"]["disabled_features"]) == 1


async def test_get_income_stability_invalid_account_id(client, db_session):
    response = await client.get("/api/v1/bank/diagnostic/income-stability?account_id=not-a-uuid")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_ACCOUNT_ID"


async def test_get_abm_found(client, db_session):
    account = Account(id=uuid.uuid4(), user_id=uuid.uuid4(), account_number_hash="v" * 64, bank_name="GTBank")
    db_session.add(account)
    await db_session.commit()

    db_session.add_all(
        [
            BankTransaction(
                id=uuid.uuid4(),
                account_id=account.id,
                transaction_date=d,
                amount=50000000,
                original_currency="NGN",
                type=TransactionType.credit,
                balance_after=50000000,
                data_source=BankTransactionDataSource.generic_csv,
            )
            for d in [date(2025, 4, 15), date(2025, 10, 15), date(2026, 1, 15), date(2026, 4, 1)]
        ]
    )
    await db_session.commit()

    response = await client.get(f"/api/v1/bank/diagnostic/abm?account_id={account.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["abm_3m"] == 50000000.0


async def test_get_abm_disabled_with_no_data(client, db_session):
    account = Account(id=uuid.uuid4(), user_id=uuid.uuid4(), account_number_hash="t" * 64, bank_name="GTBank")
    db_session.add(account)
    await db_session.commit()

    response = await client.get(f"/api/v1/bank/diagnostic/abm?account_id={account.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["data"] is None
    assert len(body["meta"]["disabled_features"]) == 1


async def test_get_abm_invalid_account_id(client, db_session):
    response = await client.get("/api/v1/bank/diagnostic/abm?account_id=not-a-uuid")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_ACCOUNT_ID"


async def test_get_cashflow_analysis_against_known_fixture(client, db_session):
    """The task's explicit ask: a fixture statement with known recurring
    vs. variable outflows."""
    account = Account(
        id=uuid.uuid4(), user_id=uuid.uuid4(), account_number_hash="u" * 64, closing_balance=446500000
    )
    db_session.add(account)
    await db_session.commit()

    balance = 500000000
    transactions = []
    for month in (1, 2, 3):
        d = date(2026, month, 5)
        balance -= 50000000
        transactions.append(
            BankTransaction(
                id=uuid.uuid4(),
                account_id=account.id,
                transaction_date=d,
                amount=-50000000,
                original_currency="NGN",
                type=TransactionType.debit,
                description="Standing Order - Office Rent Payment",
                payee_normalized="Landlord Co",
                balance_after=balance,
                data_source=BankTransactionDataSource.generic_csv,
            )
        )
    db_session.add_all(transactions)
    await db_session.commit()

    response = await client.get(f"/api/v1/bank/diagnostic/cashflow-analysis?account_id={account.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["recurring_vs_variable"]["recurring_total"] == 150000000.0
    assert body["data"]["recurring_vs_variable"]["variable_total"] == 0.0


async def test_get_cashflow_analysis_invalid_account_id(client, db_session):
    response = await client.get("/api/v1/bank/diagnostic/cashflow-analysis?account_id=not-a-uuid")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_ACCOUNT_ID"




async def _make_account_with_stable_income(db_session) -> Account:
    account = Account(id=uuid.uuid4(), user_id=uuid.uuid4(), account_number_hash="l" * 64, bank_name="GTBank")
    db_session.add(account)
    await db_session.commit()

    rows = []
    balance = 100000000
    for day_base in (1, 32, 63, 94):
        d = date(2026, 1, 1) + timedelta(days=day_base - 1)
        balance += 50000000
        rows.append(
            BankTransaction(
                id=uuid.uuid4(), account_id=account.id, transaction_date=d, amount=50000000,
                original_currency="NGN", type=TransactionType.credit, balance_after=balance,
                payee_normalized="Salary Inc", data_source=BankTransactionDataSource.generic_csv,
            )
        )
        balance -= 12000000
        rows.append(
            BankTransaction(
                id=uuid.uuid4(), account_id=account.id, transaction_date=d + timedelta(days=2), amount=-12000000,
                original_currency="NGN", type=TransactionType.debit, balance_after=balance,
                payee_normalized="Landlord Rent", data_source=BankTransactionDataSource.generic_csv,
            )
        )
    db_session.add_all(rows)
    await db_session.commit()
    return account


async def test_get_lender_brief_returns_all_sections(client, db_session, monkeypatch):
    account = await _make_account_with_stable_income(db_session)

    async def fake_generate_text(prompt, **kwargs):
        return json.dumps(
            [
                {
                    "id": "rec-1",
                    "trigger_condition": "Stable income with healthy cash buffer",
                    "entity_type": "account",
                    "entity_id": str(account.id),
                    "entity_name": "Checking Account",
                    "revenue_at_stake": 0.0,
                    "currency": "NGN",
                    "recommended_action": "Approve for a working-capital line.",
                    "reasoning": "Stable income, no fraud flags.",
                    "confidence_score": 0.9,
                    "urgency": "this_month",
                    "created_at": "2026-06-29T00:00:00Z",
                }
            ]
        )

    monkeypatch.setattr("app.services.recommendation_generation.generate_text", fake_generate_text)

    response = await client.get(f"/api/v1/bank/ai/lender-brief?account_id={account.id}")

    assert response.status_code == 200
    body = response.json()
    data = body["data"]
    # 3.2: the lender brief was rebuilt into six deterministic prose
    # sections (see bank_lender_brief.py SECTION_NAMES) -- this test
    # predates that rebuild and asserted the old dict-shaped section names
    # and a structured `lender_recommendation` list, neither of which the
    # current response produces.
    assert set(data["sections"].keys()) == {
        "business_overview",
        "income_summary",
        "expense_summary",
        "risk_assessment",
        "creditworthiness_assessment",
        "recommendation",
    }
    for name, text in data["sections"].items():
        assert isinstance(text, str) and text.strip(), f"section {name} is not readable prose"
    assert "Approve for a working-capital line." in data["sections"]["recommendation"]
    assert "loan_readiness_score" in data["key_metrics"]
    assert data["data_source_footnote"]
    assert data["pdf_url"]


async def test_get_lender_brief_invalid_account_id(client, db_session):
    response = await client.get("/api/v1/bank/ai/lender-brief?account_id=not-a-uuid")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_ACCOUNT_ID"


async def test_get_financial_health_playbook_returns_valid_recommendations(client, db_session, monkeypatch):
    """Same integration pattern as the Ecommerce (4.2) and Sales (4.3)
    playbook tests, bank-specific fixtures."""
    account = await _make_account_with_stable_income(db_session)

    async def fake_generate_text(prompt, **kwargs):
        return json.dumps(
            [
                {
                    "id": "rec-1",
                    "trigger_condition": "Stable income with healthy cash buffer",
                    "entity_type": "account",
                    "entity_id": str(account.id),
                    "entity_name": "Checking Account",
                    "revenue_at_stake": 0.0,
                    "currency": "NGN",
                    "recommended_action": "Offer a revolving credit facility.",
                    "reasoning": "Income is stable and cash buffer is healthy.",
                    "confidence_score": 0.85,
                    "urgency": "this_month",
                    "created_at": "2026-06-29T00:00:00Z",
                }
            ]
        )

    monkeypatch.setattr("app.services.recommendation_generation.generate_text", fake_generate_text)

    response = await client.get(f"/api/v1/bank/ai/financial-health-playbook?account_id={account.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["disabled_features"] == []
    recommendations = body["data"]["recommendations"]
    assert len(recommendations) == 1
    assert recommendations[0]["entity_id"] == str(account.id)


async def test_get_financial_health_playbook_invalid_account_id(client, db_session):
    response = await client.get("/api/v1/bank/ai/financial-health-playbook?account_id=not-a-uuid")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_ACCOUNT_ID"
