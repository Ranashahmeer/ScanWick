from typing import Optional

from app.models.bank_transactions import BankTransaction
from app.services.bank_cashflow import eligible_transactions
from app.services.bank_loan_readiness import compute_abm, compute_daily_closing_balances


def get_abm_response(transactions: list[BankTransaction]) -> tuple[Optional[dict], list]:
    """GET /api/v1/bank/diagnostic/abm. Reuses compute_abm() /
    compute_daily_closing_balances() (built for 3.12's loan-readiness
    composite score) as their own standalone endpoint. Returns (data,
    disabled_features)."""
    eligible = eligible_transactions(transactions)
    daily_balances = compute_daily_closing_balances(eligible)
    result = compute_abm(daily_balances)

    if result is None:
        disabled_features = [
            {
                "feature_name": "abm",
                "reason": "Not enough daily closing balance data to compute a 3-month and 12-month average.",
                "data_needed": "At least 3 months of bank transactions with balance_after populated.",
            }
        ]
        return None, disabled_features

    return result, []
