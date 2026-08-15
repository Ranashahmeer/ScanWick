from fastapi.responses import JSONResponse

from app.models.auth import User
from app.schemas.envelope import error_response
from app.services.plan_permissions import AccessLevel, FeatureAccess, get_access

FREE_TIER = "free"
BASIC_TIER = "basic"
PREMIUM_TIER = "premium"

# Ordering, not just membership — a rank comparison (not a fixed
# "== premium" / "== basic" check) is what makes a 3rd tier a one-line
# extension instead of a rewrite next time. Unknown/unset tiers rank
# below FREE_TIER (see gate_premium_components' fail-closed default).
_TIER_RANK = {FREE_TIER: 0, BASIC_TIER: 1, PREMIUM_TIER: 2}


def gate_premium_components(components: list[dict], subscription_tier: str) -> list[dict]:
    """Task 5.6: enforces the `_requires: "basic"/"premium"` markers
    already present on every health-score component in
    `app/utils/analyzer.py` (built across 13 industry scorers).

    Rank-based: a component with `_requires: "basic"` is visible to
    basic-and-premium users, locked for free users; `_requires: "premium"`
    is visible to premium users only. A component with no `_requires` key
    is never gated (free-tier accessible by default). The response stays a
    200 with every ungated component's real value intact, not a blanket
    request denial — most of a lower-tier user's score is still genuinely
    useful. The locked placeholder embeds the same `{code, message}` shape
    `error_response()` uses for its `error` key, so "upgrade required" is
    represented consistently with every other error in this codebase even
    though the overall HTTP response is still a success."""
    user_rank = _TIER_RANK.get(subscription_tier, -1)  # fails closed: unknown tier ranks below even FREE_TIER

    gated = []
    for component in components:
        required_tier = component.get("_requires")
        required_rank = _TIER_RANK.get(required_tier, 0) if required_tier else 0
        if user_rank >= required_rank:
            gated.append(component)
            continue
        gated.append(
            {
                "name": component["name"],
                "locked": True,
                "upgrade_required": True,
                "error": error_response(
                    "UPGRADE_REQUIRED",
                    f'"{component["name"]}" is a {required_tier} feature. Upgrade your plan to unlock it.',
                )["error"],
            }
        )
    return gated


async def check_feature_access(user: User, feature_key: str) -> tuple[JSONResponse | None, FeatureAccess | None]:
    """Plan-tier gate for the real bank/ecommerce endpoints, backed by
    `app/services/plan_permissions.py` — the single file that decides what
    each plan includes. Mirrors `rbac.check_role`'s exact tuple-of-
    (error_response_or_None, value) convention, called inline in the route
    body right after the existing `check_role(...)` call, so a route's
    access chain reads as "does this user belong to this merchant, then
    does their plan include this feature" — never a raised HTTPException.

    NONE -> the caller returns the JSONResponse as-is. LIMITED -> the
    caller gets the FeatureAccess back so it can shape its own response
    (see the `_limit_*`/`_shape_*` helpers next to each LIMITED-tier route)
    and should surface `access.detail` to the frontend via
    `success_response(..., plan_access=access)`. FULL -> same, but no
    shaping needed."""
    access = get_access(feature_key, user.subscription_tier)
    if access.level == AccessLevel.NONE:
        return (
            JSONResponse(
                status_code=403,
                content=error_response(
                    "UPGRADE_REQUIRED",
                    "Upgrade your plan to access this feature.",
                    details={"feature": feature_key},
                ),
            ),
            None,
        )
    return None, access
