from fastapi import APIRouter

from app.schemas.envelope import success_response
from app.services.plan_permissions import all_features_by_category

router = APIRouter(prefix="/api/v1/plans", tags=["plans"])


@router.get("/permissions")
async def get_plan_permissions():
    """Public, no auth — the full Free/Basic/Premium matrix from
    `app/services/plan_permissions.py`, serialized for the frontend (locked
    nav items, upgrade CTAs, limited-access banners) to render against
    without hardcoding its own copy of the rules."""
    data = {
        category: [
            {
                "key": feature.key,
                "label": feature.label,
                "implemented": feature.implemented,
                "access": {
                    tier: {"level": access.level.value, "detail": access.detail}
                    for tier, access in feature.access.items()
                },
            }
            for feature in features
        ]
        for category, features in all_features_by_category().items()
    }
    return success_response(data)
