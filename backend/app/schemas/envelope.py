from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.plan_permissions import FeatureAccess


def success_response(
    data: Any,
    *,
    missing_fields: list[str] | None = None,
    disabled_features: list[dict] | None = None,
    analysis_run_id: str | None = None,
    plan_access: "FeatureAccess | None" = None,
) -> dict:
    """Build the standard success envelope: {success, data, meta}.

    `disabled_features` items follow the shared shape:
    {feature_name, reason, data_needed}.

    `plan_access` is set by routes gated via
    `entitlements.check_feature_access` when the caller's tier only grants
    LIMITED access — carries the plan_permissions.py `detail` string (e.g.
    "Top 1 leak only") so the frontend can show why the response looks
    smaller than usual, without the frontend needing its own copy of the
    permissions matrix logic.
    """
    return {
        "success": True,
        "data": data,
        "meta": {
            "missing_fields": missing_fields or [],
            "disabled_features": disabled_features or [],
            "analysis_run_id": analysis_run_id,
            "plan_access": {"level": plan_access.level.value, "detail": plan_access.detail} if plan_access else None,
        },
    }


def error_response(code: str, message: str, details: dict | None = None) -> dict:
    """Build the standard error envelope: {success: false, error}."""
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
    }
