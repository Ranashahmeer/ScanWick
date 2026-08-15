from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounts import Account
from app.models.bank_transactions import BankTransaction

DEFAULT_BALANCE_TOLERANCE = 0.01
DEFAULT_TRANSFER_AMOUNT_TOLERANCE = 0.01
DEFAULT_TRANSFER_DATE_TOLERANCE_DAYS = 2


def compute_balance_integrity(
    opening_balance: Decimal,
    total_credits: Decimal,
    total_debits: Decimal,
    closing_balance: Decimal,
    tolerance: Decimal = DEFAULT_BALANCE_TOLERANCE,
) -> dict:
    """Per spec exactly: opening_balance + total_credits - total_debits must
    equal closing_balance within `tolerance` (0.01, in base currency).
    Doesn't block anything — just reports pass/fail and the discrepancy, per
    spec's "do not block the analysis, show the warning clearly".
    """
    computed_closing_balance = opening_balance + total_credits - total_debits
    discrepancy = abs(computed_closing_balance - closing_balance)
    passed = discrepancy <= tolerance
    return {
        "computed_closing_balance": computed_closing_balance,
        "balance_integrity_passed": passed,
        "balance_discrepancy": None if passed else discrepancy,
    }


def derive_balance_integrity_inputs_from_rows(canonical_rows: list[dict]) -> Optional[dict]:
    """Derives opening_balance/closing_balance from the first/last row's
    `balance_after` — the bank's own stated running balance at each point,
    and the closest proxy available to "stated on the statement" without a
    dedicated statement-header parser (none of the three ingestion sources
    extract header metadata separately from transaction rows). Returns None
    if no row has a balance_after at all (nothing to derive from).
    """
    rows_with_balance = [r for r in canonical_rows if r.get("balance_after") is not None]
    if not rows_with_balance:
        return None

    first, last = rows_with_balance[0], rows_with_balance[-1]
    opening_balance = first["balance_after"] - first["amount"]
    closing_balance = last["balance_after"]
    total_credits = sum((r["amount"] for r in canonical_rows if r["amount"] and r["amount"] > 0), 0)
    total_debits = sum((abs(r["amount"]) for r in canonical_rows if r["amount"] and r["amount"] < 0), 0)

    return {
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
        "total_credits": total_credits,
        "total_debits": total_debits,
    }


def compute_balance_integrity_for_rows(canonical_rows: list[dict], tolerance: Decimal = DEFAULT_BALANCE_TOLERANCE) -> dict:
    """Combines the two functions above into what ingest_bank_dataframe
    actually needs to populate on the Account row. All fields are None when
    there's nothing to derive from (no balance column in the source data) —
    matching the nullable columns on `accounts`, not a forced 0."""
    inputs = derive_balance_integrity_inputs_from_rows(canonical_rows)
    if inputs is None:
        return {
            "opening_balance": None,
            "closing_balance": None,
            "computed_closing_balance": None,
            "balance_integrity_passed": None,
            "balance_discrepancy": None,
        }

    integrity = compute_balance_integrity(
        inputs["opening_balance"], inputs["total_credits"], inputs["total_debits"], inputs["closing_balance"], tolerance
    )
    return {
        "opening_balance": inputs["opening_balance"],
        "closing_balance": inputs["closing_balance"],
        **integrity,
    }


async def detect_own_account_transfers(
    db: AsyncSession,
    user_id,
    amount_tolerance: Decimal = DEFAULT_TRANSFER_AMOUNT_TOLERANCE,
    date_tolerance_days: int = DEFAULT_TRANSFER_DATE_TOLERANCE_DAYS,
) -> int:
    """Finds transactions across this user's *own* accounts that look like a
    transfer between those accounts — a debit in one account matched by a
    same-magnitude credit in a *different* account of the same user, within
    a few days — and marks both is_own_account_transfer=True so they're
    excluded from inflow/outflow totals later (spec: "A transfer from GTBank
    to Access Bank for the same business must not appear as both an inflow
    and an outflow").

    Greedy first-match pairing, not a general assignment-optimization
    solver: if a user has two unrelated transfers of the exact same amount
    on the exact same day, this may pair them arbitrarily rather than
    necessarily matching the "correct" pair — a stated limitation, not a
    silent one. Needs at least 2 accounts to find anything by definition.
    """
    account_ids = (await db.execute(select(Account.id).where(Account.user_id == user_id))).scalars().all()
    if len(account_ids) < 2:
        return 0

    transactions = (
        (await db.execute(select(BankTransaction).where(BankTransaction.account_id.in_(account_ids))))
        .scalars()
        .all()
    )

    debits = [t for t in transactions if t.amount < 0 and not t.is_own_account_transfer]
    credits = [t for t in transactions if t.amount > 0 and not t.is_own_account_transfer]

    matched_count = 0
    used_credit_ids = set()
    for debit in debits:
        for credit in credits:
            if credit.id in used_credit_ids:
                continue
            if credit.account_id == debit.account_id:
                continue  # must be a transfer to a *different* account to count
            if abs(abs(debit.amount) - credit.amount) > amount_tolerance:
                continue
            if abs((credit.transaction_date - debit.transaction_date).days) > date_tolerance_days:
                continue

            debit.is_own_account_transfer = True
            credit.is_own_account_transfer = True
            used_credit_ids.add(credit.id)
            matched_count += 1
            break

    await db.commit()
    return matched_count
