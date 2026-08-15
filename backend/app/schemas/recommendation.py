from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, ValidationError


class AIRecommendation(BaseModel):
    id: str
    trigger_condition: str
    entity_type: Literal["sku", "deal", "rep", "customer", "account"]
    entity_id: str
    entity_name: str
    revenue_at_stake: float
    currency: str
    recommended_action: str
    reasoning: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    urgency: Literal["this_week", "this_month", "this_quarter"]
    created_at: datetime


def parse_recommendations(raw_recommendations: list[dict]) -> list[AIRecommendation]:
    """Validate raw recommendation dicts, dropping any missing/invalid required field."""
    valid: list[AIRecommendation] = []
    for raw in raw_recommendations:
        try:
            valid.append(AIRecommendation.model_validate(raw))
        except ValidationError:
            continue
    return valid
