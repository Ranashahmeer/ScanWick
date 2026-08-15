import json
import re

from app.schemas.recommendation import AIRecommendation, parse_recommendations
from app.services.ai_client import GeminiAPIError, generate_text

_PROMPT_TEMPLATE = """You are a business analytics assistant for Scanwick, generating actionable recommendations for a {analyzer_type} analysis.

Based on the data below, generate a list of specific, actionable recommendations. Return ONLY a JSON array (no markdown, no explanation, no surrounding text) where each object has EXACTLY these fields:
- id: a unique string identifier for this recommendation
- trigger_condition: the specific condition in the data that triggered this recommendation
- entity_type: one of "sku", "deal", "rep", "customer", "account"
- entity_id: the ID of the specific entity this recommendation is about
- entity_name: a human-readable name for that entity
- revenue_at_stake: a number representing the revenue impact
- currency: the 3-letter currency code
- recommended_action: a specific, actionable recommendation
- reasoning: why this recommendation makes sense given the data
- confidence_score: a number between 0.0 and 1.0
- urgency: one of "this_week", "this_month", "this_quarter"
- created_at: an ISO 8601 timestamp

Data:
{context_data_json}

Return ONLY the JSON array, nothing else."""


def _strip_markdown_fences(text: str) -> str:
    """Gemini commonly wraps JSON responses in markdown code fences
    (```json ... ```) despite being asked not to — stripped defensively
    rather than treating an otherwise-valid, just-wrapped response as a
    parse failure."""
    stripped = text.strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL)
    return match.group(1) if match else stripped


async def generate_recommendations(
    analyzer_type: str, context_data: dict, *, timeout: float = 30.0
) -> list[AIRecommendation]:
    """Shared by every analyzer's AI playbook endpoint (Ecommerce, Sales,
    Bank) — built once, here, per the task's own explicit "build together,
    both of you need it" framing, rather than duplicated per vertical.

    Calls Gemini (`app/services/ai_client.py`, step 0.7), then validates
    *every* returned recommendation against `AIRecommendation`
    (`app/schemas/recommendation.py`, step 1.4) via `parse_recommendations()`
    — which already drops anything missing a required field — never
    trusting raw LLM output directly. A failed Gemini call or a
    non-JSON/non-list response degrades to an empty list (logged, not
    raised) rather than crashing the caller's playbook endpoint over an
    AI provider hiccup.

    `timeout` is exposed (default unchanged at 30s for existing callers)
    so callers with a hard latency budget -- like 4.6's lender-brief,
    which must complete within 10 seconds total -- can tighten it rather
    than hoping Gemini happens to respond quickly enough."""
    prompt = _PROMPT_TEMPLATE.format(
        analyzer_type=analyzer_type, context_data_json=json.dumps(context_data, default=str, indent=2)
    )

    try:
        raw_text = await generate_text(prompt, timeout=timeout)
    except GeminiAPIError as exc:
        print(f"[recommendations] Gemini call failed for analyzer_type={analyzer_type}: {exc}")
        return []

    try:
        raw_recommendations = json.loads(_strip_markdown_fences(raw_text))
    except (json.JSONDecodeError, TypeError):
        print(f"[recommendations] Gemini returned non-JSON output for analyzer_type={analyzer_type}: {raw_text[:200]}")
        return []

    if not isinstance(raw_recommendations, list):
        print(f"[recommendations] Gemini returned a non-list JSON value for analyzer_type={analyzer_type}")
        return []

    return parse_recommendations(raw_recommendations)
