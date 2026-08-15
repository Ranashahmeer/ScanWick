import pytest
from pydantic import ValidationError

from app.schemas.recommendation import AIRecommendation, parse_recommendations

VALID_PAYLOAD = {
    "id": "rec_uuid",
    "trigger_condition": "negative net margin on top-30 SKU",
    "entity_type": "sku",
    "entity_id": "SKU-0015",
    "entity_name": "Blue Linen Shirt",
    "revenue_at_stake": 204900.00,
    "currency": "NGN",
    "recommended_action": "Pause ad spend on this SKU",
    "reasoning": "Ad spend is 181800 of the 320000 leak driver",
    "confidence_score": 0.89,
    "urgency": "this_week",
    "created_at": "2026-06-09T10:22:00Z",
}


def test_valid_recommendation_constructs():
    rec = AIRecommendation.model_validate(VALID_PAYLOAD)
    assert rec.id == "rec_uuid"
    assert rec.entity_type == "sku"
    assert rec.urgency == "this_week"
    assert rec.confidence_score == 0.89


@pytest.mark.parametrize("missing_field", list(VALID_PAYLOAD.keys()))
def test_missing_required_field_raises(missing_field):
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != missing_field}
    with pytest.raises(ValidationError):
        AIRecommendation.model_validate(payload)


def test_invalid_entity_type_raises():
    payload = {**VALID_PAYLOAD, "entity_type": "not_a_real_entity"}
    with pytest.raises(ValidationError):
        AIRecommendation.model_validate(payload)


def test_invalid_urgency_raises():
    payload = {**VALID_PAYLOAD, "urgency": "tomorrow"}
    with pytest.raises(ValidationError):
        AIRecommendation.model_validate(payload)


def test_confidence_score_out_of_range_raises():
    payload = {**VALID_PAYLOAD, "confidence_score": 1.5}
    with pytest.raises(ValidationError):
        AIRecommendation.model_validate(payload)


def test_parse_recommendations_drops_invalid_keeps_valid():
    invalid_missing_field = {k: v for k, v in VALID_PAYLOAD.items() if k != "reasoning"}
    invalid_urgency = {**VALID_PAYLOAD, "id": "rec_2", "urgency": "tomorrow"}
    valid_second = {**VALID_PAYLOAD, "id": "rec_3"}

    result = parse_recommendations([VALID_PAYLOAD, invalid_missing_field, invalid_urgency, valid_second])

    assert [r.id for r in result] == ["rec_uuid", "rec_3"]


def test_parse_recommendations_empty_list_returns_empty():
    assert parse_recommendations([]) == []
