import json

from app.services import recommendation_generation
from app.services.ai_client import GeminiAPIError
from app.services.recommendation_generation import generate_recommendations

VALID_RECOMMENDATION = {
    "id": "rec-1",
    "trigger_condition": "negative net margin in top-30 SKUs",
    "entity_type": "sku",
    "entity_id": "SKU-0042",
    "entity_name": "Blue Linen Shirt",
    "revenue_at_stake": 94200.00,
    "currency": "NGN",
    "recommended_action": "Renegotiate shipping cost with carrier or raise price by 8%.",
    "reasoning": "Ad spend accounts for 65% of this SKU's margin loss.",
    "confidence_score": 0.82,
    "urgency": "this_week",
    "created_at": "2026-06-29T00:00:00Z",
}

INVALID_RECOMMENDATION_MISSING_FIELD = {
    "id": "rec-2",
    "trigger_condition": "missing reasoning field entirely",
    "entity_type": "deal",
    "entity_id": "deal-123",
    "entity_name": "Acme Corp Renewal",
    "revenue_at_stake": 50000.00,
    "currency": "NGN",
    "recommended_action": "Follow up immediately.",
    # "reasoning" deliberately omitted -- a required field.
    "confidence_score": 0.5,
    "urgency": "this_month",
    "created_at": "2026-06-29T00:00:00Z",
}


async def test_valid_and_invalid_recommendation_only_valid_survives(monkeypatch):
    """The task's explicit ask: mock Gemini returning one valid and one
    invalid (missing-field) recommendation, asserting only the valid one
    survives."""

    async def fake_generate_text(prompt, **kwargs):
        return json.dumps([VALID_RECOMMENDATION, INVALID_RECOMMENDATION_MISSING_FIELD])

    monkeypatch.setattr(recommendation_generation, "generate_text", fake_generate_text)

    result = await generate_recommendations("ecommerce", {"some": "context"})

    assert len(result) == 1
    assert result[0].id == "rec-1"
    assert result[0].entity_name == "Blue Linen Shirt"


async def test_strips_markdown_code_fences(monkeypatch):
    async def fake_generate_text(prompt, **kwargs):
        return f"```json\n{json.dumps([VALID_RECOMMENDATION])}\n```"

    monkeypatch.setattr(recommendation_generation, "generate_text", fake_generate_text)

    result = await generate_recommendations("sales", {})

    assert len(result) == 1
    assert result[0].id == "rec-1"


async def test_gemini_failure_returns_empty_list_not_a_crash(monkeypatch):
    async def fake_generate_text(prompt, **kwargs):
        raise GeminiAPIError("simulated outage")

    monkeypatch.setattr(recommendation_generation, "generate_text", fake_generate_text)

    result = await generate_recommendations("bank", {})

    assert result == []


async def test_non_json_response_returns_empty_list_not_a_crash(monkeypatch):
    async def fake_generate_text(prompt, **kwargs):
        return "I'm sorry, I can't help with that right now."

    monkeypatch.setattr(recommendation_generation, "generate_text", fake_generate_text)

    result = await generate_recommendations("ecommerce", {})

    assert result == []


async def test_non_list_json_response_returns_empty_list(monkeypatch):
    async def fake_generate_text(prompt, **kwargs):
        return json.dumps({"not": "a list"})

    monkeypatch.setattr(recommendation_generation, "generate_text", fake_generate_text)

    result = await generate_recommendations("ecommerce", {})

    assert result == []


async def test_prompt_includes_analyzer_type_and_context_data(monkeypatch):
    captured_prompt = {}

    async def fake_generate_text(prompt, **kwargs):
        captured_prompt["value"] = prompt
        return json.dumps([])

    monkeypatch.setattr(recommendation_generation, "generate_text", fake_generate_text)

    await generate_recommendations("sales", {"deal_count": 42})

    assert "sales" in captured_prompt["value"]
    assert "42" in captured_prompt["value"]


async def test_timeout_is_passed_through_to_generate_text(monkeypatch):
    """Callers with a hard latency budget (4.6's lender-brief) need to
    tighten the default 30s timeout."""
    captured = {}

    async def fake_generate_text(prompt, **kwargs):
        captured["timeout"] = kwargs.get("timeout")
        return json.dumps([])

    monkeypatch.setattr(recommendation_generation, "generate_text", fake_generate_text)

    await generate_recommendations("bank", {}, timeout=8.0)

    assert captured["timeout"] == 8.0
