from typing import Optional

from app.models.bank_transactions import BankTransaction
from app.services.bank_cashflow import eligible_transactions, monthly_cashflow
from app.services.bank_loan_readiness import MIN_MONTHS_FOR_INCOME_STABILITY, compute_income_stability


def get_income_stability_response(transactions: list[BankTransaction]) -> tuple[Optional[dict], list]:
    """GET /api/v1/bank/diagnostic/income-stability. Reuses
    compute_income_stability() (built for 3.12's loan-readiness composite
    score) as its own standalone endpoint rather than duplicating the
    coefficient-of-variation logic. Returns (data, disabled_features)."""
    eligible = eligible_transactions(transactions)
    monthly = monthly_cashflow(eligible)
    result = compute_income_stability(monthly)

    if result is None:
        disabled_features = [
            {
                "feature_name": "income_stability",
                "reason": f"Fewer than {MIN_MONTHS_FOR_INCOME_STABILITY} months of transaction data are available.",
                "data_needed": f"At least {MIN_MONTHS_FOR_INCOME_STABILITY} months of bank transactions.",
            }
        ]
        return None, disabled_features

    return result, []
