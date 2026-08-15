import statistics
from decimal import Decimal
from typing import Optional

from app.models.accounts import Account
from app.models.bank_transactions import BankTransaction
from app.services.bank_cashflow import effective_amount, eligible_transactions

# Spec's exact weights (sum to 1.00).
SCORE_WEIGHTS = {
    "z_score_anomaly": 0.30,
    "structuring": 0.30,
    "duplicate_payee": 0.20,
    "timing_anomaly": 0.20,
}

ROUND_NUMBER_MODULUS = 1000
ROUND_NUMBER_FLAG_THRESHOLD_PCT = 30.0  # same threshold as the existing Rule 1
Z_SCORE_THRESHOLD = 3.0  # same threshold as the existing Rule 3
RAPID_IN_OUT_WINDOW_DAYS = 3
RAPID_IN_OUT_AMOUNT_TOLERANCE_PCT = 5.0  # "similar magnitude" = within 5% of each other
CONTRIBUTORY_SAVINGS_TERMS = ("ajo", "esusu", "adashe")
MIN_CONTRIBUTORY_SAVINGS_PAYMENTS = 3
MAX_CONTRIBUTORY_SAVINGS_CADENCE_DAYS = 45

# Score ≥ threshold maps to the named level; falls through to "low" otherwise.
_RISK_LEVEL_THRESHOLDS = [(75.0, "critical"), (50.0, "high"), (25.0, "medium")]


def _risk_level(score: float) -> str:
    for threshold, level in _RISK_LEVEL_THRESHOLDS:
        if score >= threshold:
            return level
    return "low"


def _contributory_savings_text(transaction: BankTransaction) -> str:
    return " ".join(filter(None, (transaction.payee_normalized, transaction.description))).lower()


def _detect_contributory_savings(transactions: list[BankTransaction]) -> tuple[list[dict], set]:
    """Recognise named, recurring ajo/esusu/adashe contributions.

    A keyword by itself is not enough to override a fraud rule. The pattern
    must contain at least three debit contributions, on separate dates, with
    a regular enough cadence and broadly similar amounts. When it qualifies,
    only those identified transactions are excluded from z-score and
    round-number structuring detection; all unrelated activity continues
    through the fraud rules unchanged.
    """
    candidates = [
        transaction
        for transaction in transactions
        if transaction.amount < 0 and any(term in _contributory_savings_text(transaction) for term in CONTRIBUTORY_SAVINGS_TERMS)
    ]
    if len(candidates) < MIN_CONTRIBUTORY_SAVINGS_PAYMENTS:
        return [], set()

    candidates.sort(key=lambda transaction: transaction.transaction_date)
    dates = [transaction.transaction_date for transaction in candidates]
    intervals = [(current - previous).days for previous, current in zip(dates, dates[1:])]
    amounts = [abs(effective_amount(transaction)) for transaction in candidates]
    median_amount = float(statistics.median(amounts))
    amount_consistent = median_amount > 0 and all(abs(amount - median_amount) / median_amount <= 0.20 for amount in amounts)
    cadence_consistent = bool(intervals) and all(0 < interval <= MAX_CONTRIBUTORY_SAVINGS_CADENCE_DAYS for interval in intervals)
    if not (amount_consistent and cadence_consistent and len(set(dates)) >= MIN_CONTRIBUTORY_SAVINGS_PAYMENTS):
        return [], set()

    average_interval = round(sum(intervals) / len(intervals), 1)
    signal = {
        "signal_type": "contributory_savings",
        "affected_transaction_count": len(candidates),
        "cadence_days": average_interval,
        "description": (
            f"Detected a recurring named contributory-savings pattern ({len(candidates)} ajo/esusu/adashe contributions, "
            f"approximately every {average_interval} days). These contributions are excluded from z-score and structuring flags."
        ),
    }
    return [signal], {transaction.id for transaction in candidates}


def _detect_z_score_anomalies(transactions: list[BankTransaction]) -> list[dict]:
    """Extends the existing statistical-outlier rule (utils/analyzer.py's
    _analyze_bank_statement, Rule 3) from "debits only, aggregate count" to
    "any transaction, individually flagged": flags any transaction whose
    amount is more than Z_SCORE_THRESHOLD standard deviations from the mean
    of all transaction amounts on this account. The distribution itself is
    computed in base currency (audit #24) — comparing a mix of raw
    original-currency amounts would be comparing apples to oranges on any
    account with more than one transaction currency; the flag's own
    displayed amount/description still show the raw amount + original
    currency, since that's what actually happened on that one transaction."""
    amounts = [float(effective_amount(t)) for t in transactions]
    if len(amounts) <= 5:
        return []
    mean = statistics.mean(amounts)
    stdev = statistics.pstdev(amounts)
    if stdev == 0:
        return []

    flags = []
    for t in transactions:
        z = (float(effective_amount(t)) - mean) / stdev
        if abs(z) > Z_SCORE_THRESHOLD:
            # "above"/"below" must track the sign of z — a large debit
            # (negative amount) pulls z negative, meaning it's *below* the
            # mean, not above it, even though its magnitude is unusual.
            direction = "above" if z > 0 else "below"
            flags.append(
                {
                    "flag_type": "z_score_anomaly",
                    "description": (
                        f"1 transaction on {t.transaction_date.isoformat()} "
                        f"({t.original_currency} {abs(t.amount):,.2f}) is {abs(z):.1f} standard "
                        f"deviations {direction} average."
                    ),
                    "transaction_id": str(t.id),
                    "amount": t.amount,
                    "z_score": round(z, 1),
                    "severity": "high" if abs(z) > 5 else ("medium" if abs(z) > 4 else "low"),
                }
            )
    return flags


def _detect_structuring(transactions: list[BankTransaction], *, excluded_transaction_ids: set | None = None) -> list[dict]:
    """Extends the existing round-number-clustering rule (Rule 1) — same
    >30%-of-debits-are-multiples-of-1000 threshold, renamed/reframed to
    spec's "structuring" category: round-number clustering is a classic
    structuring indicator (breaking amounts into round, less-scrutinized
    sums to stay under reporting/review thresholds)."""
    excluded_transaction_ids = excluded_transaction_ids or set()
    debits = [t for t in transactions if t.amount < 0 and t.id not in excluded_transaction_ids]
    if not debits:
        return []
    round_debits = [t for t in debits if abs(t.amount) % ROUND_NUMBER_MODULUS == 0]
    round_pct = len(round_debits) / len(debits) * 100
    if round_pct <= ROUND_NUMBER_FLAG_THRESHOLD_PCT:
        return []

    return [
        {
            "flag_type": "structuring",
            "description": (
                f"{len(round_debits)} of {len(debits)} debits ({round_pct:.1f}%) are exact "
                f"multiples of {ROUND_NUMBER_MODULUS} — a pattern consistent with structuring "
                "(breaking amounts into round, less-scrutinized sums)."
            ),
            "transaction_id": None,
            # Base-currency total (audit #24) — round_debits can span more
            # than one original currency; summing raw amounts would mix
            # currencies. The round-number classification itself (above)
            # stays on the raw amount deliberately: whether a number is
            # "round" is a property of how it was stated in its own
            # currency, not of its converted value.
            "amount": sum((effective_amount(t) for t in round_debits), 0),
            "affected_transaction_count": len(round_debits),
            "severity": "high" if round_pct > 60 else ("medium" if round_pct > 45 else "low"),
        }
    ]


def _detect_duplicate_payee(transactions: list[BankTransaction]) -> list[dict]:
    """Extends the existing duplicate-transaction rule (Rule 4: same amount
    + same date only) by also requiring a matching payee — same amount,
    same date, AND same payee_normalized is a meaningfully stronger signal
    than amount+date alone, which could just be coincidence (e.g. two
    unrelated NGN 5,000 transactions on the same day to different payees
    shouldn't flag; two to the *same* payee is a real duplicate-charge
    signal).

    Debits only (audit #26): the flag's own language — "possible duplicate
    or double-charge" — describes being charged twice, which only makes
    sense for money leaving the account. Two same-day, same-amount
    *incoming* payments from the same counterparty (e.g. two separate
    invoices paid by the same customer) are ordinary, not fraud-flavored,
    and were previously mislabeled with double-charge language."""
    groups: dict[tuple, list[BankTransaction]] = {}
    for t in transactions:
        if not t.payee_normalized or t.amount >= 0:
            continue
        key = (t.amount, t.transaction_date, t.payee_normalized)
        groups.setdefault(key, []).append(t)

    flags = []
    for (amount, txn_date, payee), group in groups.items():
        if len(group) < 2:
            continue
        flags.append(
            {
                "flag_type": "duplicate_payee",
                "description": (
                    f"{len(group)} transactions of {group[0].original_currency} {abs(amount):,.2f} "
                    f"to '{payee}' on {txn_date.isoformat()} — possible duplicate or double-charge."
                ),
                "transaction_id": str(group[0].id),
                "amount": amount,
                "duplicate_count": len(group),
                "severity": "medium" if len(group) > 2 else "low",
            }
        )
    return flags


def _detect_timing_anomalies(transactions: list[BankTransaction]) -> list[dict]:
    """New category — not present in the existing 5 rules at this
    granularity. Extends the *spirit* of the existing monthly "rapid
    in-out" rule (Rule 2: aggregate inflow/outflow both >2x average in the
    same month) down to individual transaction pairs: a credit followed
    within RAPID_IN_OUT_WINDOW_DAYS by a debit of similar magnitude — funds
    passing through quickly, a pattern associated with pass-through/
    layering activity rather than normal account use."""
    credits = sorted((t for t in transactions if t.amount > 0), key=lambda t: t.transaction_date)
    debits = [t for t in transactions if t.amount < 0]

    flags = []
    matched_debit_ids = set()
    for credit in credits:
        for debit in debits:
            if debit.id in matched_debit_ids:
                continue
            days_apart = (debit.transaction_date - credit.transaction_date).days
            if not (0 <= days_apart <= RAPID_IN_OUT_WINDOW_DAYS):
                continue
            # Base-currency comparison (audit #24) — the credit and its
            # matching debit could in principle be in different original
            # currencies; magnitude must be compared on a common basis.
            credit_effective = effective_amount(credit)
            debit_effective = effective_amount(debit)
            magnitude_diff_pct = abs(abs(debit_effective) - credit_effective) / credit_effective * 100
            if magnitude_diff_pct > RAPID_IN_OUT_AMOUNT_TOLERANCE_PCT:
                continue

            flags.append(
                {
                    "flag_type": "timing_anomaly",
                    "description": (
                        f"{credit.original_currency} {credit.amount:,.2f} credited on "
                        f"{credit.transaction_date.isoformat()} was largely paid back out "
                        f"{days_apart} day(s) later on {debit.transaction_date.isoformat()} — "
                        "a pattern consistent with funds passing through quickly."
                    ),
                    "transaction_id": str(credit.id),
                    "amount": credit.amount,
                    "days_between": days_apart,
                    "severity": "medium" if days_apart <= 1 else "low",
                }
            )
            matched_debit_ids.add(debit.id)
            break
    return flags


def _category_subscore(flags: list[dict]) -> float:
    """Each flagged instance contributes 25 points to its category's
    sub-score, capped at 100. Simple and monotonic by design — stated
    here, not hidden — per spec's "not a black box" requirement applying to
    the scoring methodology, not just the flag descriptions."""
    return min(100.0, len(flags) * 25.0)


def _statement_integrity(account: Optional[Account], transactions: list[BankTransaction]) -> dict:
    balance_check = "not_checked"
    if account is not None and account.balance_integrity_passed is not None:
        balance_check = "passed" if account.balance_integrity_passed else "failed"

    sorted_txns = sorted(transactions, key=lambda t: t.transaction_date)

    date_continuity = "passed"
    for prev, curr in zip(sorted_txns, sorted_txns[1:]):
        if (curr.transaction_date - prev.transaction_date).days > 30:
            date_continuity = "failed"
            break

    sequential_ordering = "passed"
    rows_with_balance = [t for t in sorted_txns if t.balance_after is not None]
    for prev, curr in zip(rows_with_balance, rows_with_balance[1:]):
        expected = prev.balance_after + curr.amount
        if abs(expected - curr.balance_after) > 0.01:
            sequential_ordering = "failed"
            break

    return {
        "balance_check": balance_check,
        "date_continuity": date_continuity,
        "sequential_ordering": sequential_ordering,
    }


def compute_fraud_risk(account: Optional[Account], transactions: list[BankTransaction]) -> dict:
    """Spec: GET /api/v1/bank/predictive/fraud-risk.

    Bug found and fixed during the 3.14 checkpoint: this function used to
    exclude nothing by itself, relying on callers to pre-filter — but the
    standalone fraud-risk route only filtered is_anomalous (via its own
    DB query), never is_own_account_transfer, while compute_loan_readiness
    (which calls this internally) DID pre-filter both. The same function
    silently behaved differently depending on how it was reached. Now
    calls the shared eligible_transactions() directly, matching every
    other Bank predictive function's pattern (loan-readiness, cashflow-
    forecast, income-stability, abm, cashflow-analysis all already call
    it internally — this was the one outlier). Own-account transfers could otherwise skew
    z-score/structuring/duplicate-payee detection, since they're not real
    external economic activity."""
    eligible = eligible_transactions(transactions)
    positive_signals, contributory_transaction_ids = _detect_contributory_savings(eligible)
    fraud_candidates = [transaction for transaction in eligible if transaction.id not in contributory_transaction_ids]
    z_score_flags = _detect_z_score_anomalies(fraud_candidates)
    structuring_flags = _detect_structuring(eligible, excluded_transaction_ids=contributory_transaction_ids)
    duplicate_flags = _detect_duplicate_payee(eligible)
    timing_flags = _detect_timing_anomalies(eligible)

    subscores = {
        "z_score_anomaly": _category_subscore(z_score_flags),
        "structuring": _category_subscore(structuring_flags),
        "duplicate_payee": _category_subscore(duplicate_flags),
        "timing_anomaly": _category_subscore(timing_flags),
    }
    fraud_risk_score = round(
        sum(float(SCORE_WEIGHTS[category]) * subscores[category] for category in SCORE_WEIGHTS)
    )

    return {
        "fraud_risk_score": fraud_risk_score,
        "risk_level": _risk_level(fraud_risk_score),
        "flags": z_score_flags + structuring_flags + duplicate_flags + timing_flags,
        "positive_signals": positive_signals,
        "statement_integrity": _statement_integrity(account, transactions),
        "score_breakdown": {
            "z_score_flags_weight": float(SCORE_WEIGHTS["z_score_anomaly"]),
            "structuring_flags_weight": float(SCORE_WEIGHTS["structuring"]),
            "duplicate_payee_weight": float(SCORE_WEIGHTS["duplicate_payee"]),
            "timing_anomaly_weight": float(SCORE_WEIGHTS["timing_anomaly"]),
        },
    }


_FLAG_SAFE_KEYS = {"flag_type", "severity", "z_score", "affected_transaction_count"}


def redact_flags_for_loan_officer(flags: list[dict]) -> list[dict]:
    """Task 5.3: a Loan Officer (and Bank Viewer) must never receive
    transaction-level detail from fraud-risk's `flags` -- each flag's
    `transaction_id`, `amount`, and free-text `description` (which embeds
    transaction_date/amount/payee for z_score/duplicate_payee/timing
    flags) are dropped. Allowlist-based, not a denylist/strip: any future
    field added to a flag dict is excluded by default unless explicitly
    added to `_FLAG_SAFE_KEYS` -- fails closed, not open."""
    return [{key: value for key, value in flag.items() if key in _FLAG_SAFE_KEYS} for flag in flags]
