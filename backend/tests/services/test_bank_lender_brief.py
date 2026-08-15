import asyncio
import json
import time
import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.models.bank_transactions import BankTransaction, BankTransactionDataSource, TransactionType
from app.services import bank_lender_brief
from app.services.bank_lender_brief import SECTION_NAMES, _render_lender_brief_pdf, get_lender_brief_response


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
    """Same realistic, multi-component-eligible fixture pattern used by
    test_bank_loan_readiness.py -- 4 months of stable salary/rent/utility
    activity, enough for income-stability, ABM, and loan-readiness to all
    produce real (non-disabled) results."""
    rows = []
    balance = 100000000
    for day_base in (1, 32, 63, 94):
        d = date(2026, 1, 1) + timedelta(days=day_base - 1)
        balance += 50000000
        rows.append(_txn("500000", d, balance, "Salary Inc"))
        balance -= 12000000
        rows.append(_txn("-120000", d + timedelta(days=2), balance, "Landlord Rent"))
        balance -= 3000000
        rows.append(_txn("-30000", d + timedelta(days=5), balance, "Utility Co"))
    return rows


_VALID_RECOMMENDATION = {
    "id": "rec-1",
    "trigger_condition": "Loan readiness score is in the top tier with stable income",
    "entity_type": "account",
    "entity_id": "acct-1",
    "entity_name": "Checking Account",
    "revenue_at_stake": 0.0,
    "currency": "NGN",
    "recommended_action": "Approve for a working-capital line up to 3x average monthly inflow.",
    "reasoning": "Stable income, healthy cash buffer, no fraud flags.",
    "confidence_score": 0.9,
    "urgency": "this_month",
    "created_at": "2026-06-29T00:00:00Z",
}


async def test_all_six_sections_plus_key_metrics_and_footnote_present(monkeypatch):
    """The task's explicit content test: all six sections, key_metrics,
    and data_source_footnote are present."""

    async def fake_generate_text(prompt, **kwargs):
        return json.dumps([_VALID_RECOMMENDATION])

    monkeypatch.setattr("app.services.recommendation_generation.generate_text", fake_generate_text)

    data = await get_lender_brief_response(None, _four_month_fixture())

    assert set(SECTION_NAMES) == set(data["sections"].keys())
    for section_name in SECTION_NAMES:
        assert data["sections"][section_name] is not None

    assert data["sections"]["recommendation"].startswith("Approve for a working-capital line")
    assert all(isinstance(data["sections"][name], str) for name in SECTION_NAMES)
    assert not any("{'" in data["sections"][name] for name in SECTION_NAMES)
    assert "loan_readiness_score" in data["key_metrics"]
    assert "fraud_risk_score" in data["key_metrics"]
    assert data["data_source_footnote"]
    assert "is_anomalous" in data["data_source_footnote"]
    assert data["pdf_url"]


async def test_generates_within_ten_second_budget_with_realistic_gemini_latency(monkeypatch):
    """The task's explicit timing test: mocked Gemini call with realistic
    latency, asserting total generation completes within the 10-second
    budget."""

    async def slow_generate_text(prompt, **kwargs):
        await asyncio.sleep(2.0)  # realistic Gemini round-trip latency
        return json.dumps([_VALID_RECOMMENDATION])

    monkeypatch.setattr("app.services.recommendation_generation.generate_text", slow_generate_text)

    start = time.monotonic()
    data = await get_lender_brief_response(None, _four_month_fixture())
    elapsed = time.monotonic() - start

    assert elapsed < 10.0
    assert data["sections"]["recommendation"].startswith("Approve for a working-capital line")


async def test_handles_gemini_failure_gracefully_within_budget(monkeypatch):
    """Lender-recommendation falls back to an empty list (4.1's own
    failure behavior) rather than the whole brief crashing or stalling
    past budget."""
    from app.services.ai_client import GeminiAPIError

    async def failing_generate_text(prompt, **kwargs):
        raise GeminiAPIError("simulated outage")

    monkeypatch.setattr("app.services.recommendation_generation.generate_text", failing_generate_text)

    data = await get_lender_brief_response(None, _four_month_fixture())

    assert data["sections"]["recommendation"].startswith("Review the verified income")
    assert data["key_metrics"]["loan_readiness_score"] is not None


def test_pdf_renderer_wraps_prose_without_raw_dictionary_strings():
    sections = {name: "A complete lender-facing sentence. " * 35 for name in SECTION_NAMES}
    pdf = _render_lender_brief_pdf(uuid.uuid4(), sections, {"loan_readiness_score": 72}, "Verified source record.")

    document = bank_lender_brief.fitz.open(stream=pdf, filetype="pdf")
    text = "".join(page.get_text() for page in document)
    assert document.page_count > 1
    assert "Business Overview" in text
    assert "{" not in text
