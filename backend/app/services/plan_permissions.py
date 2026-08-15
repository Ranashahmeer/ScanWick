"""The single source of truth for what Free/Basic/Premium include.

Edit this file to change what any plan gets — nothing else needs to
change. Every row from the plan/permissions matrix lives here, including
the handful with no backend feature to gate yet (`implemented=False`) and
the Platform/General rows that describe the *aggregate* effect of the
per-feature rows below rather than one endpoint (`enforcement="aggregate"`)
— kept so this file stays the complete reference, not just the enforced
subset. See `app/services/entitlements.py::check_feature_access` for how a
route consults this, and `app/routes/plans.py` for the read-only endpoint
the frontend fetches this from.
"""

from dataclasses import dataclass, field
from enum import Enum


class AccessLevel(str, Enum):
    FULL = "full"
    LIMITED = "limited"
    NONE = "none"


@dataclass(frozen=True)
class FeatureAccess:
    level: AccessLevel
    # The PDF's own limited-access phrasing, e.g. "Top 1 leak only" — shown
    # to the user (see LimitedAccessBanner on the frontend) and, for the
    # bespoke-shaping endpoints, used by the route to decide exactly what
    # to trim (see the `_limit_*`/`_shape_*` helpers in bank.py/ecommerce.py/
    # sales.py).
    detail: str | None = None


FULL = FeatureAccess(AccessLevel.FULL)
NONE = FeatureAccess(AccessLevel.NONE)


@dataclass(frozen=True)
class PlanFeature:
    key: str
    category: str
    label: str
    access: dict[str, FeatureAccess]
    implemented: bool = True
    # "route" | "aggregate" (documents an overall effect, not one endpoint)
    enforcement: str = "route"
    note: str | None = None


PLAN_FEATURES: list[PlanFeature] = [
    # ── Platform / General ───────────────────────────────────────────────
    PlanFeature(
        key="platform.upload_data",
        category="Platform / General",
        label="Upload data",
        access={"free": FULL, "basic": FULL, "premium": FULL},
        enforcement="aggregate",
        note="Ingestion endpoints are never tier-blocked — ingesting more data only ever helps a lower tier's free insight be accurate.",
    ),
    PlanFeature(
        key="platform.data_quality_report",
        category="Platform / General",
        label="Data Quality Report",
        access={"free": FULL, "basic": FULL, "premium": FULL},
        enforcement="aggregate",
    ),
    PlanFeature(
        key="platform.summary_dashboard",
        category="Platform / General",
        label="One summary dashboard per module",
        access={"free": FULL, "basic": FULL, "premium": FULL},
        enforcement="aggregate",
        note="Realized per-vertical: bank.dashboard_summary, ecommerce.dashboard_summary.",
    ),
    PlanFeature(
        key="platform.monthly_trend_chart",
        category="Platform / General",
        label="Monthly trend chart",
        access={"free": FULL, "basic": FULL, "premium": FULL},
        implemented=False,
        enforcement="aggregate",
        note="No dedicated endpoint found — not yet built as a standalone feature.",
    ),
    PlanFeature(
        key="platform.one_insight_per_module",
        category="Platform / General",
        label="One real insight per module (Free hook)",
        access={"free": FULL, "basic": FULL, "premium": FULL},
        enforcement="aggregate",
        note="Realized via the LIMITED tier of bank.loan_readiness.",
    ),
    PlanFeature(
        key="platform.full_analytics_dashboards",
        category="Platform / General",
        label="Full analytics dashboards",
        access={"free": NONE, "basic": FULL, "premium": FULL},
        enforcement="aggregate",
        note="Describes the combined effect of every individual dashboard/diagnostic row below — not a distinct endpoint.",
    ),
    PlanFeature(
        key="platform.ai_playbooks_explainability",
        category="Platform / General",
        label="AI recommendation playbooks + explainability",
        access={"free": NONE, "basic": NONE, "premium": FULL},
        enforcement="aggregate",
        note="Realized by bank.lender_brief, bank.financial_health_playbook.",
    ),
    PlanFeature(
        key="platform.intelligence_center",
        category="Platform / General",
        label="Intelligence Center",
        access={"free": NONE, "basic": FeatureAccess(AccessLevel.LIMITED, "Partial"), "premium": FULL},
        enforcement="aggregate",
        note="Describes the overall nav/section access already implemented per-feature (sidebar locking) — not a distinct endpoint.",
    ),
    PlanFeature(
        key="platform.report_exports",
        category="Platform / General",
        label="Report exports",
        access={"free": NONE, "basic": FeatureAccess(AccessLevel.LIMITED, "Basic reports"), "premium": FULL},
        note=(
            "Realized by app/routes/reports.py: Basic gets single-vertical library templates and PDF only "
            "(no Executive Overview, custom builder, Excel, or scheduling); Premium gets everything."
        ),
    ),
    # ── E-Commerce Analyzer ──────────────────────────────────────────────
    PlanFeature(
        key="ecommerce.dashboard_summary",
        category="E-Commerce Analyzer",
        label="Summary dashboard",
        access={"free": FULL, "basic": FULL, "premium": FULL},
    ),
    PlanFeature(
        key="ecommerce.net_margin_dashboard",
        category="E-Commerce Analyzer",
        label="Net margin dashboard",
        access={"free": NONE, "basic": FULL, "premium": FULL},
    ),
    # ── Bank Statement Analyzer ──────────────────────────────────────────
    PlanFeature(
        key="bank.dashboard_summary",
        category="Bank Statement Analyzer",
        label="Financial summary dashboard",
        access={"free": NONE, "basic": FULL, "premium": FULL},
    ),
    PlanFeature(
        key="bank.loan_readiness",
        category="Bank Statement Analyzer",
        label="Loan readiness",
        access={
            "free": FeatureAccess(AccessLevel.LIMITED, "Grade only (A/B/C/D)"),
            "basic": FeatureAccess(AccessLevel.LIMITED, "Score + grade + tier"),
            "premium": FeatureAccess(AccessLevel.FULL, "Full breakdown + improvement plan"),
        },
    ),
    PlanFeature(
        key="bank.income_stability",
        category="Bank Statement Analyzer",
        label="Income stability",
        access={"free": NONE, "basic": FULL, "premium": FULL},
    ),
    PlanFeature(
        key="bank.abm",
        category="Bank Statement Analyzer",
        label="Account Behavior Monitoring (ABM)",
        access={"free": NONE, "basic": FULL, "premium": FULL},
    ),
    PlanFeature(
        key="bank.cashflow_analysis",
        category="Bank Statement Analyzer",
        label="Cashflow analysis",
        access={"free": NONE, "basic": FULL, "premium": FULL},
    ),
    PlanFeature(
        key="bank.statement_integrity",
        category="Bank Statement Analyzer",
        label="Statement integrity",
        access={"free": NONE, "basic": FULL, "premium": FULL},
        note="Served from the Fraud Risk endpoint's statement_integrity sub-object — see bank.fraud_risk for the score/flags themselves.",
    ),
    PlanFeature(
        key="bank.fraud_risk",
        category="Bank Statement Analyzer",
        label="Fraud risk score",
        access={
            "free": NONE,
            "basic": FeatureAccess(AccessLevel.LIMITED, "Statement integrity only — no fraud score/flags"),
            "premium": FULL,
        },
        note="Same endpoint as bank.statement_integrity — Basic sees statement_integrity only, Premium sees the full fraud score + flags.",
    ),
    PlanFeature(
        key="bank.cashflow_forecast",
        category="Bank Statement Analyzer",
        label="90-day cashflow forecast",
        access={"free": NONE, "basic": NONE, "premium": FULL},
    ),
    PlanFeature(
        key="bank.lender_brief",
        category="Bank Statement Analyzer",
        label="AI lender brief (incl. downloadable PDF)",
        access={"free": NONE, "basic": NONE, "premium": FULL},
        note="The JSON response's pdf_url field covers the 'downloadable PDF' row too — one endpoint, one gate.",
    ),
    PlanFeature(
        key="bank.financial_health_playbook",
        category="Bank Statement Analyzer",
        label="Financial health playbook",
        access={"free": NONE, "basic": NONE, "premium": FULL},
    ),
]

_BY_KEY: dict[str, PlanFeature] = {feature.key: feature for feature in PLAN_FEATURES}


def get_access(feature_key: str, tier: str) -> FeatureAccess:
    """Fails closed: an unknown feature key or unknown tier is treated as
    NONE rather than silently allowing access."""
    feature = _BY_KEY.get(feature_key)
    if feature is None:
        return NONE
    return feature.access.get(tier, NONE)


def all_features_by_category() -> dict[str, list[PlanFeature]]:
    grouped: dict[str, list[PlanFeature]] = {}
    for feature in PLAN_FEATURES:
        grouped.setdefault(feature.category, []).append(feature)
    return grouped
