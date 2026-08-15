from decimal import Decimal
from typing import Optional

from app.models.accounts import Account
from app.models.bank_transactions import BankTransaction
from app.services.bank_cashflow import effective_amount, eligible_transactions, monthly_cashflow

# This build's own stated choice — task 2.12 doesn't give an explicit
# count for "top payees"/"top income sources" (unlike e.g. ecommerce's
# "top-30 by revenue", which the task itself states).
TOP_N_PAYEES = 10


def _credit_debit_split(transactions: list[BankTransaction]) -> dict:
    credit_count = sum(1 for t in transactions if t.amount > 0)
    debit_count = sum(1 for t in transactions if t.amount < 0)
    total = credit_count + debit_count
    return {
        "credit_count": credit_count,
        "debit_count": debit_count,
        "credit_pct": round(credit_count / total * 100, 1) if total else 0.0,
        "debit_pct": round(debit_count / total * 100, 1) if total else 0.0,
    }


def _top_payees(transactions: list[BankTransaction], *, direction: str) -> list[dict]:
    """direction='outflow' groups debits by payee; direction='inflow' groups
    credits. Transactions with no payee_normalized are skipped — there's no
    meaningful payee-level grouping for an unidentified counterparty."""
    by_payee: dict[str, dict] = {}
    for t in transactions:
        if not t.payee_normalized:
            continue
        is_outflow = t.amount < 0
        if direction == "outflow" and not is_outflow:
            continue
        if direction == "inflow" and is_outflow:
            continue
        bucket = by_payee.setdefault(t.payee_normalized, {"total": 0, "occurrence_count": 0})
        bucket["total"] += abs(effective_amount(t))
        bucket["occurrence_count"] += 1

    ranked = sorted(by_payee.items(), key=lambda kv: kv[1]["total"], reverse=True)[:TOP_N_PAYEES]
    key_name = "total_outflow" if direction == "outflow" else "total_inflow"
    return [
        {"payee": payee, key_name: data["total"], "occurrence_count": data["occurrence_count"]}
        for payee, data in ranked
    ]


def compute_dashboard_summary(account: Optional[Account], transactions: list[BankTransaction]) -> dict:
    """GET /api/v1/bank/dashboard/summary. Excludes is_anomalous and
    is_own_account_transfer transactions from every aggregate (via the
    shared `eligible_transactions`, same exclusion used by every Bank
    predictive model)."""
    eligible = eligible_transactions(transactions)

    inflows = sum((effective_amount(t) for t in eligible if t.amount > 0), 0)
    outflows = sum((abs(effective_amount(t)) for t in eligible if t.amount < 0), 0)

    opening_balance = account.opening_balance if account else None
    closing_balance = account.closing_balance if account else None
    net_change = (
        closing_balance - opening_balance if opening_balance is not None and closing_balance is not None else None
    )

    monthly = monthly_cashflow(eligible)
    monthly_cashflow_trend = [
        {"month": month, "inflow": bucket["inflow"], "outflow": bucket["outflow"]}
        for month, bucket in monthly.items()
    ]

    return {
        "inflows": inflows,
        "outflows": outflows,
        "balance": {
            "opening_balance": opening_balance,
            "closing_balance": closing_balance,
            "net_change": net_change,
        },
        "credit_debit_split": _credit_debit_split(eligible),
        "top_payees_by_outflow": _top_payees(eligible, direction="outflow"),
        "top_income_sources": _top_payees(eligible, direction="inflow"),
        "monthly_cashflow_trend": monthly_cashflow_trend,
    }
