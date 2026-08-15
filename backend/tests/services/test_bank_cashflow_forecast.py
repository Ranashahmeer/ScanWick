import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.models.accounts import Account
from app.models.bank_transactions import BankTransaction, BankTransactionDataSource, TransactionType
from app.services.bank_cashflow_forecast import (
    FORECAST_DAYS,
    _days_in_month,
    _detect_recurring_commitments,
    compute_cashflow_forecast,
)


def _txn(amount, txn_date, balance_after=None, payee=None) -> BankTransaction:
    return BankTransaction(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        transaction_date=txn_date,
        amount=int(float(amount) * 100),
        original_currency="NGN",
        type=TransactionType.credit if int(float(amount) * 100) >= 0 else TransactionType.debit,
        balance_after=int(float(balance_after) * 100) if balance_after is not None else None,
        payee_normalized=payee,
        data_source=BankTransactionDataSource.generic_csv,
    )


def _burning_business_fixture() -> list[BankTransaction]:
    """4 months where rent + utilities exceed income — a real net burn, so
    cash_runway is well-defined (finite) in both scenarios, and the stress
    scenario (reduced income) has something meaningful to shorten."""
    rows = []
    balance = 500000000
    for day_base in (1, 32, 63, 94):
        d = date(2026, 1, 1) + timedelta(days=day_base - 1)
        balance += 40000000
        rows.append(_txn("400000", d, balance, "Salary Inc"))
        balance -= 50000000
        rows.append(_txn("-500000", d + timedelta(days=2), balance, "Landlord Rent"))
        balance -= 5000000
        rows.append(_txn("-50000", d + timedelta(days=5), balance, "Utility Co"))
    return rows


def test_forecast_produces_exactly_90_daily_points():
    result, disabled_features = compute_cashflow_forecast(_burning_business_fixture())
    assert result["forecast_days"] == FORECAST_DAYS
    assert len(result["daily_forecast"]) == 90
    assert disabled_features == []  # every row has balance_after -- no fallback needed


def test_daily_forecast_points_are_sequential_and_have_widening_confidence_bands():
    result, _ = compute_cashflow_forecast(_burning_business_fixture())
    points = result["daily_forecast"]

    base = date.fromisoformat(result["base_date"])
    for i, point in enumerate(points, start=1):
        assert date.fromisoformat(point["date"]) == base + timedelta(days=i)
        assert point["confidence_lower_80"] <= point["projected_balance"] <= point["confidence_upper_80"]

    first_band_width = points[0]["confidence_upper_80"] - points[0]["confidence_lower_80"]
    last_band_width = points[-1]["confidence_upper_80"] - points[-1]["confidence_lower_80"]
    assert last_band_width > first_band_width  # uncertainty compounds with time


def test_stress_scenario_produces_shorter_runway_than_primary():
    """The task's explicit ask."""
    result, _ = compute_cashflow_forecast(_burning_business_fixture())
    runway = result["cash_runway"]

    assert runway["primary_scenario_months"] is not None
    assert runway["stress_scenario_months"] is not None
    assert runway["stress_scenario_months"] < runway["primary_scenario_months"]
    assert runway["stress_assumption"] == "20% reduction in income"


def test_cash_runway_is_none_when_cash_flow_positive():
    """Running out of money doesn't apply to a business gaining cash."""
    rows = []
    balance = 100000000
    for day_base in (1, 32, 63):
        d = date(2026, 1, 1) + timedelta(days=day_base - 1)
        balance += 90000000
        rows.append(_txn("900000", d, balance, "Salary Inc"))
        balance -= 5000000
        rows.append(_txn("-50000", d + timedelta(days=2), balance, "Utility Co"))

    result, _ = compute_cashflow_forecast(rows)
    assert result["cash_runway"]["primary_scenario_months"] is None


def test_recurring_commitments_detected_with_amount_and_projected_dates():
    rows = _burning_business_fixture()
    base_date = date(2026, 4, 9)  # matches the fixture's last transaction date

    commitments = _detect_recurring_commitments(rows, base_date)
    by_payee = {c["payee"]: c for c in commitments}

    assert "Landlord Rent" in by_payee
    assert by_payee["Landlord Rent"]["amount"] == 50000000
    assert len(by_payee["Landlord Rent"]["expected_dates"]) >= 1
    for d in by_payee["Landlord Rent"]["expected_dates"]:
        assert (date.fromisoformat(d) - base_date).days <= FORECAST_DAYS


def test_recurring_commitments_excludes_one_off_payees():
    rows = [
        _txn("-500000", date(2026, 1, 3), payee="Landlord Rent"),
        _txn("-500000", date(2026, 2, 3), payee="Landlord Rent"),
        _txn("-75000", date(2026, 1, 15), payee="One-Time Repair Shop"),  # only once
    ]
    commitments = _detect_recurring_commitments(rows, date(2026, 2, 3))
    payees = {c["payee"] for c in commitments}
    assert "Landlord Rent" in payees
    assert "One-Time Repair Shop" not in payees


def test_recurring_commitments_excludes_inconsistent_amounts():
    rows = [
        _txn("-500000", date(2026, 1, 3), payee="Variable Vendor"),
        _txn("-50000", date(2026, 2, 3), payee="Variable Vendor"),  # wildly different amount
    ]
    commitments = _detect_recurring_commitments(rows, date(2026, 2, 3))
    assert commitments == []


def test_days_in_month_handles_february_and_december():
    assert _days_in_month(2026, 2) == 28
    assert _days_in_month(2024, 2) == 29  # leap year
    assert _days_in_month(2026, 12) == 31


def test_compute_cashflow_forecast_handles_empty_transactions():
    """No balance_after data anywhere and no account passed in -- the
    forecast still runs (from an assumed NGN 0 balance), but audit #22
    requires this fallback to be flagged via disabled_features rather than
    presented with the same confidence as a well-supported forecast."""
    result, disabled_features = compute_cashflow_forecast([])
    assert result["forecast_days"] == 90
    assert len(result["daily_forecast"]) == 90
    assert result["cash_runway"]["primary_scenario_months"] is None
    assert result["recurring_commitments_projected"] == []
    assert len(disabled_features) == 1
    assert disabled_features[0]["feature_name"] == "cashflow_forecast_starting_balance"
    assert "NGN 0" in disabled_features[0]["reason"]


def test_compute_cashflow_forecast_falls_back_to_account_closing_balance():
    """Audit #22: when no transaction has balance_after populated, the
    forecast must anchor to account.closing_balance (like
    bank_cashflow_analysis.py already does) instead of a fabricated NGN 0 --
    still flagged as a lower-confidence approximation."""
    account = Account(
        id=uuid.uuid4(), user_id=uuid.uuid4(), account_number_hash="x" * 64, closing_balance=250000000
    )
    rows = [_txn("400000", date(2026, 1, 1)), _txn("-100000", date(2026, 1, 5))]  # no balance_after anywhere

    result, disabled_features = compute_cashflow_forecast(rows, account)

    assert result["daily_forecast"][0]["projected_balance"] != 0
    assert len(disabled_features) == 1
    assert disabled_features[0]["feature_name"] == "cashflow_forecast_starting_balance"
    assert "closing balance" in disabled_features[0]["reason"]
