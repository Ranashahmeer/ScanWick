import textwrap
import uuid
from decimal import Decimal
from typing import Optional

import fitz  # PyMuPDF

from app.models.accounts import Account
from app.models.bank_transactions import BankTransaction
from app.services import storage
from app.services.bank_cashflow import eligible_transactions, monthly_cashflow
from app.services.bank_cashflow_analysis import compute_cashflow_analysis
from app.services.bank_fraud_risk import compute_fraud_risk
from app.services.bank_loan_readiness import (
    compute_abm,
    compute_daily_closing_balances,
    compute_income_stability,
    compute_loan_readiness,
)
from app.services.recommendation_generation import generate_recommendations

SECTION_NAMES = (
    "business_overview",
    "income_summary",
    "expense_summary",
    "risk_assessment",
    "creditworthiness_assessment",
    "recommendation",
)

LENDER_RECOMMENDATION_TIMEOUT_SECONDS = 8.0


def _money(value: Decimal | None) -> str:
    return f"NGN {value:,.2f}" if value is not None else "not available"


def _build_prose_sections(
    account: Optional[Account],
    statement_dates: list,
    eligible_count: int,
    monthly: dict,
    income_stability: Optional[dict],
    cashflow: dict,
    fraud_risk: dict,
    loan_readiness: dict,
    recommendations: list,
) -> dict[str, str]:
    bank_name = account.bank_name if account and account.bank_name else "the connected bank account"
    period = (
        f"from {statement_dates[0].isoformat()} to {statement_dates[-1].isoformat()}"
        if statement_dates
        else "with no eligible transactions"
    )
    inflow = sum((row["inflow"] for row in monthly.values()), 0)
    outflow = sum((row["outflow"] for row in monthly.values()), 0)
    income_text = (
        f"Income totals {_money(inflow)} across {len(monthly)} month(s). "
        + (
            f"Income stability is {income_stability['label']} (coefficient of variation "
            f"{income_stability['cv_pct']}%, score {income_stability['score']}/100)."
            if income_stability
            else "There is insufficient monthly history to assess income stability reliably."
        )
    )
    recurring = cashflow["recurring_vs_variable"]
    concentration = cashflow["expense_concentration_ratio_pct"]
    expense_text = (
        f"Eligible outflows total {_money(outflow)}. "
        f"Recurring spending is {_money(recurring['recurring_total'])} and variable spending is "
        f"{_money(recurring['variable_total'])}. "
        + (
            f"The three largest payees account for {concentration}% of outflows."
            if concentration is not None
            else "Expense concentration cannot be calculated because no eligible outflows were found."
        )
    )
    integrity = fraud_risk["statement_integrity"]
    integrity_text = (
        f"Balance check {integrity['balance_check']}, date continuity {integrity['date_continuity']}, "
        f"and sequential ordering {integrity['sequential_ordering']}."
    )
    risk_text = (
        f"The fraud-risk assessment is {fraud_risk['risk_level']} with a score of "
        f"{fraud_risk['fraud_risk_score']}/100 and {len(fraud_risk['flags'])} detected flag(s). "
        f"Statement integrity: {integrity_text}"
    )
    credit_text = (
        f"The loan-readiness score is {loan_readiness['loan_readiness_score']}/100 "
        f"(tier {loan_readiness['creditworthiness_tier']}: {loan_readiness['tier_definition']}). "
        f"The maximum score supported by the available data is {loan_readiness['max_achievable_score']}/100. "
        + (
            f"Cash buffer is {cashflow['cash_buffer_months']} months."
            if cashflow["cash_buffer_months"] is not None
            else "Cash-buffer evidence is unavailable."
        )
    )
    if recommendations:
        recommendation_text = recommendations[0].recommended_action
        if recommendations[0].reasoning:
            recommendation_text += f" Rationale: {recommendations[0].reasoning}"
    else:
        recommendation_text = (
            "Review the verified income, expense, risk, and creditworthiness evidence alongside the institution's "
            "lending policy before making a lending decision."
        )
    return {
        "business_overview": (
            f"This assessment covers {bank_name} {period}. It is based on {eligible_count} eligible transaction(s) "
            "after standard anomaly and own-account-transfer exclusions."
        ),
        "income_summary": income_text,
        "expense_summary": expense_text,
        "risk_assessment": risk_text,
        "creditworthiness_assessment": credit_text,
        "recommendation": recommendation_text,
    }


async def _build_sections_and_key_metrics(account: Optional[Account], transactions: list[BankTransaction]) -> tuple[dict, dict, list]:
    eligible = eligible_transactions(transactions)
    monthly = monthly_cashflow(eligible)
    income_stability = compute_income_stability(monthly)
    daily_balances = compute_daily_closing_balances(eligible)
    abm_trend = compute_abm(daily_balances)
    cashflow = compute_cashflow_analysis(account, transactions)
    fraud_risk = compute_fraud_risk(account, transactions)
    loan_readiness = compute_loan_readiness(account, transactions, fraud_risk_result=fraud_risk)
    statement_dates = sorted(t.transaction_date for t in eligible)
    context = {
        "income_stability": income_stability,
        "cashflow": {**cashflow, "abm_trend": abm_trend},
        "fraud_risk": fraud_risk,
        "loan_readiness": loan_readiness,
    }
    recommendations = await generate_recommendations("bank", context, timeout=LENDER_RECOMMENDATION_TIMEOUT_SECONDS)
    sections = _build_prose_sections(
        account, statement_dates, len(eligible), monthly, income_stability, cashflow, fraud_risk, loan_readiness, recommendations
    )
    key_metrics = {
        "loan_readiness_score": loan_readiness["loan_readiness_score"],
        "creditworthiness_tier": loan_readiness["creditworthiness_tier"],
        "fraud_risk_score": fraud_risk["fraud_risk_score"],
        "income_stability_score": income_stability["score"] if income_stability else None,
        "cash_buffer_months": cashflow["cash_buffer_months"],
    }
    return sections, key_metrics, statement_dates


def _render_lender_brief_pdf(account_id: uuid.UUID, sections: dict, key_metrics: dict, data_source_footnote: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    y = 50
    bottom_margin = page.rect.height - 50

    def write(text: str, *, font_size: int = 10) -> None:
        nonlocal page, y, bottom_margin
        for line in textwrap.wrap(text, width=95) or [""]:
            if y > bottom_margin:
                page = doc.new_page()
                y = 50
                bottom_margin = page.rect.height - 50
            page.insert_text((50, y), line, fontsize=font_size)
            y += 16 if font_size == 10 else 20

    write(f"Scanwick Lender Brief - Account {account_id}", font_size=14)
    write("")
    write("KEY METRICS", font_size=12)
    for key, value in key_metrics.items():
        write(f"{key.replace('_', ' ').title()}: {value}")
    for section_name in SECTION_NAMES:
        write("")
        write(section_name.replace("_", " ").title(), font_size=12)
        write(sections[section_name])
    write("")
    write("DATA SOURCE FOOTNOTE", font_size=12)
    write(data_source_footnote)
    return doc.tobytes()


async def get_lender_brief_response(account: Optional[Account], transactions: list[BankTransaction]) -> dict:
    sections, key_metrics, statement_dates = await _build_sections_and_key_metrics(account, transactions)
    data_source_footnote = (
        f"Based on {len(statement_dates)} transactions"
        + (f" from {statement_dates[0].isoformat()} to {statement_dates[-1].isoformat()}" if statement_dates else "")
        + ". Excludes is_anomalous and is_own_account_transfer transactions per the platform's standard "
        "data-quality exclusion rules."
    )
    account_id = account.id if account else uuid.uuid4()
    pdf_bytes = _render_lender_brief_pdf(account_id, sections, key_metrics, data_source_footnote)
    pdf_url = storage.upload_file(f"lender_briefs/{account_id}/{uuid.uuid4()}.pdf", pdf_bytes)
    return {"sections": sections, "key_metrics": key_metrics, "data_source_footnote": data_source_footnote, "pdf_url": pdf_url}
