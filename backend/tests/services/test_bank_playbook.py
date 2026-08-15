import json
import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.models.bank_transactions import BankTransaction, BankTransactionDataSource, TransactionType
from app.services import recommendation_generation
from app.services.bank_playbook import get_financial_health_playbook_response


def _txn(amount, txn_date, balance_after=None, payee=None, **overrides) -> BankTransaction:
    defaults = dict(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        transaction_date=txn_date,
        amount=int(float(amount) * 100),
        original_currency="NGN",
        type=TransactionType.credit if int(float(amount) * 100) >= 0 else TransactionType.debit,
        balance_after=int(float(balance_after) * 100) if balance_after is not None else None,
        payee_normalized=payee,
        data_source=BankTransactionDataSource.generic_csv,
    )
    defaults.update(overrides)
    return BankTransaction(**defaults)


def _four_month_fixture() -> list[BankTransaction]:
    rows = []
    balance = 100000000
    for day_base in (1, 32, 63, 94):
        d = date(2026, 1, 1) + timedelta(days=day_base - 1)
        balance += 50000000
        rows.append(_txn("500000", d, balance, "Salary Inc"))
        balance -= 12000000
        rows.append(_txn("-120000", d + timedelta(days=2), balance, "Landlord Rent"))
    return rows


VALID_RECOMMENDATION = {
    "id": "rec-1",
    "trigger_condition": "Stable income with healthy cash buffer",
    "entity_type": "account",
    "entity_id": "acct-1",
    "entity_name": "Checking Account",
    "revenue_at_stake": 0.0,
    "currency": "NGN",
    "recommended_action": "Offer a revolving credit facility.",
    "reasoning": "Income is stable and cash buffer is healthy.",
    "confidence_score": 0.85,
    "urgency": "this_month",
    "created_at": "2026-06-29T00:00:00Z",
}


async def test_returns_valid_recommendations_with_enough_data(monkeypatch):
    async def fake_generate_text(prompt, **kwargs):
        return json.dumps([VALID_RECOMMENDATION])

    monkeypatch.setattr(recommendation_generation, "generate_text", fake_generate_text)

    data, disabled_features = await get_financial_health_playbook_response(None, _four_month_fixture())

    assert disabled_features == []
    assert len(data["recommendations"]) == 1
    assert data["recommendations"][0]["id"] == "rec-1"


async def test_income_stability_disabled_below_three_months(monkeypatch):
    async def fake_generate_text(prompt, **kwargs):
        return json.dumps([])

    monkeypatch.setattr(recommendation_generation, "generate_text", fake_generate_text)

    one_month = [_txn("500000", date(2026, 1, 1), "1500000", "Salary Inc")]

    data, disabled_features = await get_financial_health_playbook_response(None, one_month)

    assert len(disabled_features) == 1
    assert disabled_features[0]["feature_name"] == "income_stability"
