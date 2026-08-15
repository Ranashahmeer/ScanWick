from decimal import Decimal
from typing import Optional

from app.models.accounts import Account
from app.models.bank_transactions import BankTransaction
from app.services.bank_cashflow import (
    detect_recurring_payees,
    effective_amount,
    eligible_transactions,
    monthly_cashflow,
)
from app.services.bank_loan_readiness import compute_cash_buffer, compute_daily_closing_balances
from app.services.bank_transaction_classification import classify_business_or_personal, classify_mode

# This build's own stated choice — task 2.15 doesn't give an explicit "top
# N" for the concentration ratio. CR3 (top 3 payees) is a conventional
# concentration-ratio window, more informative than a single top payee
# alone for judging "is spending concentrated."
EXPENSE_CONCENTRATION_TOP_N = 3


def compute_cashflow_analysis(account: Optional[Account], transactions: list[BankTransaction]) -> dict:
    """GET /api/v1/bank/diagnostic/cashflow-analysis."""
    eligible = eligible_transactions(transactions)

    daily_balances = compute_daily_closing_balances(eligible)
    current_balance = daily_balances[-1][1] if daily_balances else (account.closing_balance if account else None)
    monthly = monthly_cashflow(eligible)
    avg_monthly_outflow = (
        sum((v["outflow"] for v in monthly.values()), 0) / len(monthly) if monthly else None
    )
    cash_buffer = compute_cash_buffer(current_balance, avg_monthly_outflow)

    outflow_by_payee: dict[str, Decimal] = {}
    total_outflow = 0
    for t in eligible:
        if t.amount >= 0:
            continue
        payee = t.payee_normalized or "Unknown"
        amount = abs(effective_amount(t))
        outflow_by_payee[payee] = outflow_by_payee.get(payee, 0) + amount
        total_outflow += amount

    top_n_total = sum(sorted(outflow_by_payee.values(), reverse=True)[:EXPENSE_CONCENTRATION_TOP_N], 0)
    expense_concentration_ratio_pct = round(float(top_n_total / total_outflow * 100), 1) if total_outflow else None

    recurring = detect_recurring_payees(eligible)
    recurring_total = sum((data["total_amount"] for data in recurring.values()), 0)
    variable_total = total_outflow - recurring_total
    recurring_vs_variable = {
        "recurring_total": recurring_total,
        "variable_total": variable_total,
        "recurring_pct": round(float(recurring_total / total_outflow * 100), 1) if total_outflow else None,
        "variable_pct": round(float(variable_total / total_outflow * 100), 1) if total_outflow else None,
    }

    by_mode: dict[str, dict] = {}
    for t in eligible:
        mode = classify_mode(t.description)
        key = mode.value if mode else "unclassified"
        bucket = by_mode.setdefault(key, {"total_amount": 0, "occurrence_count": 0})
        bucket["total_amount"] += abs(effective_amount(t))
        bucket["occurrence_count"] += 1
    by_payment_mode = [{"mode": mode, **data} for mode, data in by_mode.items()]
    by_payment_mode.sort(key=lambda d: -d["total_amount"])

    # business_vs_personal is a spending-pattern classification — scoped to
    # outflows, since "is this expense business or personal" doesn't have
    # the same meaning applied to incoming money.
    by_bp: dict[str, dict] = {}
    for t in eligible:
        if t.amount >= 0:
            continue
        label = classify_business_or_personal(t.description)
        bucket = by_bp.setdefault(label, {"total_amount": 0, "occurrence_count": 0})
        bucket["total_amount"] += abs(effective_amount(t))
        bucket["occurrence_count"] += 1
    business_vs_personal = [{"category": label, **data} for label, data in by_bp.items()]
    business_vs_personal.sort(key=lambda d: -d["total_amount"])

    return {
        "cash_buffer_months": cash_buffer["buffer_months"] if cash_buffer else None,
        "expense_concentration_ratio_pct": expense_concentration_ratio_pct,
        "recurring_vs_variable": recurring_vs_variable,
        "by_payment_mode": by_payment_mode,
        "business_vs_personal": business_vs_personal,
    }
