import statistics
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from dateutil.relativedelta import relativedelta

from app.models.accounts import Account
from app.models.bank_transactions import BankTransaction
from app.services.bank_cashflow import detect_recurring_payees, eligible_transactions, monthly_cashflow
from app.services.bank_fraud_risk import compute_fraud_risk

# Spec's exact weights (sum to 1.00).
LOAN_READINESS_WEIGHTS = {
    "income_stability": 0.30,
    "abm_trend": 0.25,
    "fraud_risk_inverted": 0.25,
    "cash_buffer": 0.20,
}

MIN_MONTHS_FOR_INCOME_STABILITY = 3  # per spec, exactly
CASH_BUFFER_TARGET_MONTHS = 6  # spec's own stated "healthy" reference point (improvement_recommendations example)
RECOMMENDATION_SCORE_THRESHOLD = 70

# This implementation's own stated tiers — spec's example shows only one
# (B, "Score 60-79"); A/C/D are this build's choice, documented rather than
# left implicit.
_TIER_THRESHOLDS = [(80, "A", "Score 80-100"), (60, "B", "Score 60-79"), (40, "C", "Score 40-59")]


def _tier_for_score(score: int) -> tuple[str, str]:
    for threshold, tier, definition in _TIER_THRESHOLDS:
        if score >= threshold:
            return tier, definition
    return "D", "Score 0-39"




def compute_income_stability(monthly_cashflow: dict) -> Optional[dict]:
    """Spec exactly: coefficient of variation of monthly inflows — <20%
    stable, 20-40% moderate, >40% volatile, minimum 3 months of data.

    score = round(100 - cv_pct), clamped to [0, 100]. Spec doesn't give this
    mapping explicitly, but it reproduces spec's own worked example almost
    exactly (cv_pct=18.4 -> 81.6 -> rounds to 82, matching spec's score=82) —
    a consistency check, not proof the spec intends this exact formula.
    """
    inflows = [float(v["inflow"]) for v in monthly_cashflow.values()]
    if len(inflows) < MIN_MONTHS_FOR_INCOME_STABILITY:
        return None
    mean = statistics.mean(inflows)
    if mean == 0:
        return None
    cv_pct = (statistics.pstdev(inflows) / mean) * 100
    label = "stable" if cv_pct < 20 else ("moderate" if cv_pct <= 40 else "volatile")
    score = max(0, min(100, round(100 - cv_pct)))
    return {"score": score, "label": label, "cv_pct": round(cv_pct, 1)}


def compute_daily_closing_balances(transactions: list[BankTransaction]) -> list[tuple[date, Decimal]]:
    """One closing balance per calendar day — the last balance_after on
    that date, in the order transactions were given (the finest ordering
    available; bank_transactions has no time-of-day field, only DATE)."""
    rows = [t for t in transactions if t.balance_after is not None]
    rows.sort(key=lambda t: t.transaction_date)
    daily: dict[date, Decimal] = {}
    for t in rows:
        daily[t.transaction_date] = t.balance_after
    if not daily:
        return []

    # A quiet day closes at the previous day's closing balance.  Leaving
    # those days out would average transaction points rather than daily
    # balances and systematically understate ABM for sparse statements.
    first_date = min(daily)
    last_date = max(daily)
    carried_balance = daily[first_date]
    expanded: list[tuple[date, Decimal]] = []
    current_date = first_date
    while current_date <= last_date:
        carried_balance = daily.get(current_date, carried_balance)
        expanded.append((current_date, carried_balance))
        current_date += timedelta(days=1)
    return expanded


def _average_for_window(daily_balances: list[tuple[date, Decimal]], reference_date: date, months: int) -> Optional[Decimal]:
    window_start = reference_date - relativedelta(months=months)
    values = [bal for d, bal in daily_balances if window_start <= d <= reference_date]
    if not values:
        return None
    return sum(values, 0) / len(values)


def compute_abm(daily_balances: list[tuple[date, Decimal]]) -> Optional[dict]:
    """ABM = average of daily closing balances, per spec exactly ("not the
    average of transaction-point balances" — already true here, since
    compute_daily_closing_balances collapses to one value per day first).
    Reference date is the most recent date *in the data*, never wall-clock
    "today" — this is what makes compute_loan_readiness's score a pure
    function of its inputs, with zero dependency on when the test happens
    to run (see the rerun-stability test).
    """
    if not daily_balances:
        return None
    reference_date = daily_balances[-1][0]
    abm_3m = _average_for_window(daily_balances, reference_date, 3)
    abm_6m = _average_for_window(daily_balances, reference_date, 6)
    abm_12m = _average_for_window(daily_balances, reference_date, 12)
    if abm_3m is None or abm_12m is None:
        return None

    pct_change = float((abm_3m - abm_12m) / abm_12m * 100) if abm_12m != 0 else 0.0
    if pct_change > 2:
        trend = "improving"
    elif pct_change < -2:
        trend = "declining"
    else:
        trend = "stable"

    # Own stated scoring curve, not given by spec: 50 is neutral, +/- the
    # percentage swing between the 3-month and 12-month averages, clamped.
    score = max(0, min(100, round(50 + pct_change)))
    return {"abm_3m": abm_3m, "abm_6m": abm_6m, "abm_12m": abm_12m, "trend": trend, "score": score}


def compute_cash_buffer(current_balance: Optional[Decimal], avg_monthly_outflow: Optional[Decimal]) -> Optional[dict]:
    """buffer_months = current_balance / average monthly outflow. score
    scales linearly to 100 at CASH_BUFFER_TARGET_MONTHS (6, per spec's own
    stated target in its improvement_recommendations example) — this
    build's own stated curve, since spec gives the target but not the
    underlying formula."""
    if current_balance is None or not avg_monthly_outflow:
        return None
    buffer_months = current_balance / avg_monthly_outflow
    score = max(0, min(100, round(float(buffer_months / CASH_BUFFER_TARGET_MONTHS * 100))))
    return {"buffer_months": round(float(buffer_months), 1), "score": score}


def _detect_recurring_outflows_monthly(transactions: list[BankTransaction], num_months: int) -> Decimal:
    """Stands in for spec's "recurring outflows to financial institution
    payees" specifically, broadened to *all* recurring outflows since
    there's no institution-classification capability yet — narrower than
    spec's literal wording, documented as such, not silently over-claimed.
    Built on the shared `detect_recurring_payees` (same heuristic used by
    3.13's cashflow-forecast and 2.15's cashflow-analysis)."""
    monthly_recurring_total = 0
    for data in detect_recurring_payees(transactions).values():
        monthly_recurring_total += data["total_amount"] / num_months
    return monthly_recurring_total


def compute_estimated_debt_coverage(transactions: list[BankTransaction], monthly_cashflow: dict) -> dict:
    num_months = max(1, len(monthly_cashflow))
    total_inflow = sum((v["inflow"] for v in monthly_cashflow.values()), 0)
    total_outflow = sum((v["outflow"] for v in monthly_cashflow.values()), 0)
    estimated_available_income = (total_inflow - total_outflow) / num_months

    estimated_monthly_debt_obligations = _detect_recurring_outflows_monthly(transactions, num_months)
    coverage_ratio = (
        round(float(estimated_available_income / estimated_monthly_debt_obligations), 1)
        if estimated_monthly_debt_obligations
        else None
    )
    return {
        "estimated_available_income": estimated_available_income,
        "estimated_monthly_debt_obligations": estimated_monthly_debt_obligations,
        "coverage_ratio": coverage_ratio,
        "methodology_note": (
            "Debt obligations estimated from recurring outflows (same payee, similar amount, "
            "recurring across months) — not specifically filtered to financial-institution "
            "payees, since there's no institution-classification capability yet. This is an "
            "estimate, not a verified figure."
        ),
    }


def _build_recommendations(components: dict) -> list[dict]:
    """Only for the factors a business can actually act on — skips
    fraud_risk_inverted, since "commit less fraud" isn't an actionable
    business recommendation the way reducing expenses or smoothing income
    is. Spec's own example only shows a cash_buffer recommendation; this
    generates one per under-threshold factor, worst gap first."""
    recommendations = []

    cash_buffer = components.get("cash_buffer")
    if cash_buffer and cash_buffer["score"] < RECOMMENDATION_SCORE_THRESHOLD:
        gain = round((100 - cash_buffer["score"]) * float(LOAN_READINESS_WEIGHTS["cash_buffer"]))
        recommendations.append(
            {
                "factor": "cash_buffer",
                "current_value": f"{cash_buffer['buffer_months']} months",
                "target_value": f"{int(CASH_BUFFER_TARGET_MONTHS)}+ months",
                "action": "Reduce variable operating expenses or build up reserves to extend your cash buffer.",
                "estimated_score_gain": max(1, gain),
            }
        )

    income_stability = components.get("income_stability")
    if income_stability and income_stability["score"] < RECOMMENDATION_SCORE_THRESHOLD:
        gain = round((100 - income_stability["score"]) * float(LOAN_READINESS_WEIGHTS["income_stability"]))
        recommendations.append(
            {
                "factor": "income_stability",
                "current_value": f"{income_stability['cv_pct']}% coefficient of variation ({income_stability['label']})",
                "target_value": "below 20% (stable)",
                "action": "Diversify income sources or smooth invoicing/payment timing to reduce month-to-month inflow swings.",
                "estimated_score_gain": max(1, gain),
            }
        )

    abm_trend = components.get("abm_trend")
    # Triggered by the *label*, not the numeric score threshold: "improving"
    # is already the target state regardless of its exact score (a small-
    # magnitude improvement can still score under 70) — using the score
    # threshold here produced a nonsensical "go from improving to improving"
    # recommendation, caught by manually inspecting real output before
    # writing the formal tests.
    if abm_trend and abm_trend["trend"] != "improving":
        gain = round((100 - abm_trend["score"]) * float(LOAN_READINESS_WEIGHTS["abm_trend"]))
        recommendations.append(
            {
                "factor": "abm_trend",
                "current_value": f"trend: {abm_trend['trend']}",
                "target_value": "improving",
                "action": "Maintain higher average balances by delaying large withdrawals where possible.",
                "estimated_score_gain": max(1, gain),
            }
        )

    recommendations.sort(key=lambda r: -r["estimated_score_gain"])
    return recommendations


def compute_loan_readiness(
    account: Optional[Account],
    transactions: list[BankTransaction],
    *,
    fraud_risk_result: Optional[dict] = None,
) -> dict:
    """GET /api/v1/bank/predictive/loan-readiness. Purely a function of
    `account`/`transactions` — no wall-clock dependency anywhere in this
    module — so re-running it against the same statement always produces
    the exact same score, not just "within 1 point" (spec's stability
    requirement, exceeded rather than just met).

    `fraud_risk_result` (audit #27): callers that already need the full
    `compute_fraud_risk` result for their own purposes (e.g. the lender
    brief, which shows a dedicated risk-flags section) can pass it in to
    avoid recomputing the O(n²) z-score/structuring/duplicate/timing
    detectors a second time in the same request. Computed internally, as
    before, when omitted."""
    eligible = eligible_transactions(transactions)
    monthly = monthly_cashflow(eligible)

    income_stability = compute_income_stability(monthly)
    daily_balances = compute_daily_closing_balances(eligible)
    abm_trend = compute_abm(daily_balances)

    current_balance = daily_balances[-1][1] if daily_balances else (account.closing_balance if account else None)
    avg_monthly_outflow = (
        sum((v["outflow"] for v in monthly.values()), 0) / len(monthly) if monthly else None
    )
    cash_buffer = compute_cash_buffer(current_balance, avg_monthly_outflow)

    if fraud_risk_result is None:
        fraud_risk_result = compute_fraud_risk(account, eligible)
    raw_fraud_score = fraud_risk_result["fraud_risk_score"]
    fraud_risk_inverted = {"score": 100 - raw_fraud_score, "raw_fraud_score": raw_fraud_score}

    components = {
        "income_stability": income_stability,
        "abm_trend": abm_trend,
        "fraud_risk_inverted": fraud_risk_inverted,
        "cash_buffer": cash_buffer,
    }
    available = {k: v for k, v in components.items() if v is not None}
    disabled = [k for k, v in components.items() if v is None]

    score_breakdown: dict = {}
    loan_readiness_score = 0
    if available:
        weighted_total = 0
        for key, comp in available.items():
            fixed_weight = LOAN_READINESS_WEIGHTS[key]
            weight_pct = round(float(fixed_weight * 100), 1)
            contribution = round(comp["score"] * float(fixed_weight), 1)
            weighted_total += Decimal(str(contribution))
            extra = {k2: v2 for k2, v2 in comp.items() if k2 != "score"}
            score_breakdown[key] = {"weight_pct": weight_pct, "score": comp["score"], "contribution": contribution, **extra}
        loan_readiness_score = int(round(weighted_total))

    tier, tier_definition = _tier_for_score(loan_readiness_score)

    return {
        "loan_readiness_score": loan_readiness_score,
        "creditworthiness_tier": tier,
        "tier_definition": tier_definition,
        "score_breakdown": score_breakdown,
        "disabled_components": disabled,
        "max_achievable_score": int(sum(LOAN_READINESS_WEIGHTS[key] * 100 for key in available)),
        "improvement_recommendations": _build_recommendations(available),
        "estimated_debt_coverage_indicator": compute_estimated_debt_coverage(eligible, monthly),
    }
