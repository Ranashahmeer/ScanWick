import statistics
from datetime import date, timedelta
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
from app.services.bank_loan_readiness import compute_daily_closing_balances

FORECAST_DAYS = 90
CONFIDENCE_Z_80 = 1.2816  # two-sided 80% CI z-score (10% in each tail)
STRESS_INCOME_REDUCTION_PCT = 0.20  # spec's exact stated stress assumption: "20% reduction in income"


def _daily_net_cashflow_series(transactions: list[BankTransaction]) -> list[Decimal]:
    """One net (credit - debit) figure per calendar day that actually has a
    transaction — days with no activity aren't included as zeros, since a
    statement's "daily average" should reflect actual transaction days, not
    be diluted by gaps (which Account.statement_period vs. actual activity
    already separately captures, e.g. via date_continuity in fraud-risk)."""
    daily: dict[date, Decimal] = {}
    for t in transactions:
        daily[t.transaction_date] = daily.get(t.transaction_date, 0) + effective_amount(t)
    return [daily[d] for d in sorted(daily)]


def _forecast_daily_balances(
    current_balance: float, avg_daily_net: float, stdev_daily_net: float, base_date: date, days: int
) -> list[dict]:
    """Random-walk forecast: balance drifts by avg_daily_net per day:
    projected_balance(i) = current_balance + avg_daily_net * i. Uncertainty
    compounds with sqrt(i) (variance accumulates linearly day-over-day for
    a random walk — standard, not this build's own invention), so the 80%
    confidence band widens the further out the forecast goes, rather than
    staying a fixed +/- width."""
    forecast = []
    for i in range(1, days + 1):
        projected = current_balance + avg_daily_net * i
        band_width = float(CONFIDENCE_Z_80) * stdev_daily_net * float(i**0.5)
        forecast.append(
            {
                "date": (base_date + timedelta(days=i)).isoformat(),
                "projected_balance": projected,
                "confidence_lower_80": projected - band_width,
                "confidence_upper_80": projected + band_width,
            }
        )
    return forecast


def _cash_runway_months(current_balance: Optional[Decimal], avg_monthly_net_burn: Optional[Decimal]) -> Optional[float]:
    """Runway = how long until the balance hits zero at the current net
    burn rate (outflow minus inflow — not outflow alone, since income does
    offset expenses; this is what lets the stress scenario, which reduces
    income, actually shorten the runway). None (not a number) if the
    business is net cash-positive — "running out of money" doesn't apply
    when the balance is growing, not shrinking."""
    if current_balance is None or avg_monthly_net_burn is None or avg_monthly_net_burn <= 0:
        return None
    return round(float(current_balance / avg_monthly_net_burn), 1)


def _detect_recurring_commitments(transactions: list[BankTransaction], base_date: date) -> list[dict]:
    """Built on the shared `detect_recurring_payees` (same heuristic used by
    3.12's debt-coverage estimate and 2.15's cashflow-analysis), extended
    here to also project the *next* expected occurrence(s) within the
    forecast window — assumes a roughly monthly cadence on the same
    day-of-month as the historical payments, which is the common case for
    rent/loan/subscription payments this is meant to catch; a payee
    recurring weekly or quarterly wouldn't be projected correctly by this
    same-day-of-month assumption.
    """
    commitments = []
    for payee, data in detect_recurring_payees(transactions).items():
        target_day = data["last_transaction_date"].day
        expected_dates = []
        for month_offset in range(1, 4):  # project up to 3 months ahead, trimmed to the forecast window below
            year = base_date.year + (base_date.month - 1 + month_offset) // 12
            month = (base_date.month - 1 + month_offset) % 12 + 1
            day = min(target_day, _days_in_month(year, month))
            expected = date(year, month, day)
            if (expected - base_date).days <= FORECAST_DAYS:
                expected_dates.append(expected.isoformat())

        if expected_dates:
            commitments.append({"payee": payee, "amount": data["avg_amount"], "expected_dates": expected_dates})

    return commitments


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (date(year, month + 1, 1) - timedelta(days=1)).day


def compute_cashflow_forecast(
    transactions: list[BankTransaction], account: Optional[Account] = None
) -> tuple[dict, list]:
    """GET /api/v1/bank/predictive/cashflow-forecast. base_date is the most
    recent transaction date *in the data*, never wall-clock "today" — same
    determinism principle as 3.12's ABM reference date.

    Audit #22 fix: current_balance falls back to `account.closing_balance`
    when no transaction has `balance_after` populated — the same fallback
    `bank_cashflow_analysis.py` already uses — instead of silently starting
    the entire 90-day projection from a fabricated NGN 0 balance. Whenever
    that fallback (or, in the worst case, no balance data at all) is used,
    a `disabled_features` entry is returned alongside the forecast so the
    route can flag it as a lower-confidence approximation instead of
    presenting it with the same confidence as a well-supported forecast --
    this matters most for the lender brief, per the audit.
    """
    eligible = eligible_transactions(transactions)
    daily_balances = compute_daily_closing_balances(eligible)
    base_date = daily_balances[-1][0] if daily_balances else date.today()

    disabled_features: list[dict] = []
    if daily_balances:
        current_balance = daily_balances[-1][1]
    else:
        current_balance = account.closing_balance if account is not None else None
        if current_balance is not None:
            disabled_features.append(
                {
                    "feature_name": "cashflow_forecast_starting_balance",
                    "reason": (
                        "No transaction had balance_after populated; the forecast starts from the "
                        "account's stated closing balance rather than a balance derived from daily "
                        "transaction history -- a lower-confidence approximation."
                    ),
                    "data_needed": "Transactions with balance_after populated to derive an exact starting balance.",
                }
            )
        else:
            disabled_features.append(
                {
                    "feature_name": "cashflow_forecast_starting_balance",
                    "reason": (
                        "No transaction had balance_after populated and no account closing balance is "
                        "known; the forecast starts from an assumed NGN 0 balance -- treat the projected "
                        "balances as directional only, not an actual balance estimate."
                    ),
                    "data_needed": "Transactions with balance_after populated, or a known account closing balance.",
                }
            )
            current_balance = 0

    daily_net_series = _daily_net_cashflow_series(eligible)
    avg_daily_net = (
        sum(daily_net_series, 0) / len(daily_net_series) if daily_net_series else 0
    )
    stdev_daily_net = (
        float(statistics.pstdev([float(v) for v in daily_net_series])) if len(daily_net_series) > 1 else 0
    )

    primary_forecast = _forecast_daily_balances(current_balance, avg_daily_net, stdev_daily_net, base_date, FORECAST_DAYS)

    monthly = monthly_cashflow(eligible)
    avg_monthly_inflow = (
        sum((v["inflow"] for v in monthly.values()), 0) / len(monthly) if monthly else 0
    )
    avg_monthly_outflow = (
        sum((v["outflow"] for v in monthly.values()), 0) / len(monthly) if monthly else 0
    )
    primary_net_burn = avg_monthly_outflow - avg_monthly_inflow
    stressed_inflow = avg_monthly_inflow * (1 - STRESS_INCOME_REDUCTION_PCT)
    stress_net_burn = avg_monthly_outflow - stressed_inflow

    return {
        "forecast_days": FORECAST_DAYS,
        "base_date": base_date.isoformat(),
        "daily_forecast": primary_forecast,
        "cash_runway": {
            "primary_scenario_months": _cash_runway_months(current_balance, primary_net_burn),
            "stress_scenario_months": _cash_runway_months(current_balance, stress_net_burn),
            "stress_assumption": "20% reduction in income",
        },
        "recurring_commitments_projected": _detect_recurring_commitments(eligible, base_date),
    }, disabled_features
