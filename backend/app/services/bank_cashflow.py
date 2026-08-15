from decimal import Decimal

from app.models.bank_transactions import BankTransaction

# Heuristic recurring-payment detection — not a lookup against
# is_recurring/mode/category, none of which are populated by any ingestion
# path (1.21's stated scope). "Same payee, similar amount, more than once"
# stands in for is_recurring's own spec definition. Shared by every Bank
# feature that needs this (debt-coverage in 3.12, cashflow-forecast's
# projected commitments in 3.13, cashflow-analysis's recurring_vs_variable
# split in 2.15) rather than each one re-deriving it independently.
RECURRING_MIN_OCCURRENCES = 2
RECURRING_AMOUNT_TOLERANCE_PCT = 10


def effective_amount(t: BankTransaction) -> Decimal:
    """The transaction's amount in the account's base currency -- audit
    #24: `base_currency_amount`/`exchange_rate` are computed at ingestion
    time (`bank_ingestion.py`'s `write_canonical_bank_rows`, via
    `get_historical_rate`) but were never read by any analytics service, so
    every summed financial figure (revenue, expenses, balances) summed a
    mixed-currency row's *raw* `amount` directly into base-currency totals
    with no conversion. Falls back to the raw `amount` only when
    `base_currency_amount` is null -- which, per `write_canonical_bank_rows`,
    only happens when `get_historical_rate` found no rate for that
    (original_currency, base_currency, date) triple; for same-currency rows
    (original_currency == base_currency) the rate is always exactly 1.0 and
    base_currency_amount is always populated, so this fallback only ever
    matters for a genuinely un-rated foreign-currency row, not the common
    case. Every summed/averaged financial figure across the bank analytics
    services should read through this rather than `t.amount` directly;
    single-transaction display values (a flag's own `amount`, a duplicate-
    payee group's shared amount) intentionally keep using the raw `amount`
    + `original_currency` pair, since those describe one real transaction
    exactly as it happened, not an aggregate."""
    return t.base_currency_amount if t.base_currency_amount is not None else t.amount


def eligible_transactions(transactions: list[BankTransaction]) -> list[BankTransaction]:
    """Excludes is_anomalous (Part 1's "filter out before training/scoring"
    principle) and is_own_account_transfer (spec: these "must not appear as
    both an inflow and an outflow" — excluding them here, before any
    cashflow aggregation, is exactly that). Shared by every bank predictive
    model (fraud risk, loan readiness, cashflow forecast) rather than each
    one filtering independently."""
    return [t for t in transactions if not t.is_anomalous and not t.is_own_account_transfer]


def monthly_cashflow(transactions: list[BankTransaction]) -> dict[str, dict]:
    """Groups already-eligible transactions into {YYYY-MM: {inflow, outflow}}."""
    months: dict[str, dict] = {}
    for t in transactions:
        key = t.transaction_date.strftime("%Y-%m")
        bucket = months.setdefault(key, {"inflow": 0, "outflow": 0})
        amount = effective_amount(t)
        if amount > 0:
            bucket["inflow"] += amount
        else:
            bucket["outflow"] += abs(amount)
    return dict(sorted(months.items()))


def detect_recurring_payees(transactions: list[BankTransaction]) -> dict[str, dict]:
    """Groups debit transactions by payee_normalized, keeping only payees
    that recur at least RECURRING_MIN_OCCURRENCES times with amounts
    within RECURRING_AMOUNT_TOLERANCE_PCT of each other. Returns
    {payee: {avg_amount, total_amount, occurrences, transactions, last_transaction_date}}.
    """
    debits_by_payee: dict[str, list[BankTransaction]] = {}
    for t in transactions:
        if t.amount < 0 and t.payee_normalized:
            debits_by_payee.setdefault(t.payee_normalized, []).append(t)

    recurring: dict[str, dict] = {}
    for payee, txns in debits_by_payee.items():
        if len(txns) < RECURRING_MIN_OCCURRENCES:
            continue
        amounts = [abs(effective_amount(t)) for t in txns]
        avg_amount = sum(amounts, 0) / len(amounts)
        if avg_amount == 0:
            continue
        if not all(abs(a - avg_amount) / avg_amount * 100 <= RECURRING_AMOUNT_TOLERANCE_PCT for a in amounts):
            continue
        recurring[payee] = {
            "avg_amount": avg_amount,
            "total_amount": sum(amounts, 0),
            "occurrences": len(txns),
            "transactions": txns,
            "last_transaction_date": max(t.transaction_date for t in txns),
        }
    return recurring
