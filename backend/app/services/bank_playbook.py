from typing import Optional

from app.models.accounts import Account
from app.models.bank_transactions import BankTransaction
from app.services.bank_cashflow import eligible_transactions, monthly_cashflow
from app.services.bank_cashflow_analysis import compute_cashflow_analysis
from app.services.bank_loan_readiness import (
    MIN_MONTHS_FOR_INCOME_STABILITY,
    compute_abm,
    compute_daily_closing_balances,
    compute_income_stability,
    compute_loan_readiness,
)
from app.services.recommendation_generation import generate_recommendations


async def get_financial_health_playbook_response(
    account: Optional[Account], transactions: list[BankTransaction]
) -> tuple[dict, list]:
    """GET /api/v1/bank/ai/financial-health-playbook. Same pattern as
    Ecommerce's (4.2) playbook endpoint: gather a few real
    diagnostic/predictive results, hand them to the shared 4.1
    recommendation service, return the validated recommendations.

    Fed by income-stability, cash-flow analysis (+ABM trend), and
    loan-readiness — the three core "financial health" signals. Fraud-risk
    (a risk/fraud concern, not a health one) feeds its own endpoint
    instead, not duplicated here. Returns (data, disabled_features)
    — no analysis_run_id, consistent with every other bank endpoint, none
    of which write reconciliation reports."""
    eligible = eligible_transactions(transactions)
    monthly = monthly_cashflow(eligible)
    income_stability = compute_income_stability(monthly)
    daily_balances = compute_daily_closing_balances(eligible)
    abm_trend = compute_abm(daily_balances)
    cashflow = compute_cashflow_analysis(account, transactions)
    loan_readiness = compute_loan_readiness(account, transactions)

    disabled_features = []
    if income_stability is None:
        disabled_features.append(
            {
                "feature_name": "income_stability",
                "reason": f"Fewer than {MIN_MONTHS_FOR_INCOME_STABILITY} months of transaction data are available.",
                "data_needed": f"At least {MIN_MONTHS_FOR_INCOME_STABILITY} months of bank transactions.",
            }
        )

    context = {
        "income_stability": income_stability,
        "cash_flow_analysis": {**cashflow, "abm_trend": abm_trend},
        "loan_readiness": loan_readiness,
    }
    recommendations = await generate_recommendations("bank", context)

    data = {"recommendations": [r.model_dump(mode="json") for r in recommendations]}
    return data, disabled_features
