import uuid
from datetime import date
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounts import Account
from app.models.bank_transactions import BankTransaction
from app.models.contextual_markers import ContextualMarker
from app.models.orders import Order
from app.models.reconciliation_reports import AnalyzerType


async def get_marker_ranges(
    db: AsyncSession, merchant_id: uuid.UUID, analyzer_type: AnalyzerType
) -> list[tuple[date, date]]:
    """Fetched once per ingestion run (not once per row) so flagging N orders
    doesn't cost N queries."""
    result = await db.execute(
        select(ContextualMarker.start_date, ContextualMarker.end_date).where(
            ContextualMarker.merchant_id == merchant_id,
            ContextualMarker.analyzer_type == analyzer_type,
        )
    )
    return [(row.start_date, row.end_date) for row in result.all()]


def is_within_marker_ranges(check_date: date, ranges: list[tuple[date, date]]) -> bool:
    return any(start <= check_date <= end for start, end in ranges)


async def reflag_orders_for_marker(db: AsyncSession, marker: ContextualMarker) -> int:
    """The re-flag-on-new-marker job: sets is_anomalous=TRUE on every existing
    order for this merchant whose order_date falls inside the marker's range
    (inclusive). Does not unset orders outside the range — a different
    marker, or the same marker resized, could still cover them; full
    re-evaluation across all markers is a follow-on, not needed for the
    documented behavior ("re-flag existing records whenever a new marker is
    added")."""
    # Compare on the date portion, not the raw timestamp — order_date is a
    # TIMESTAMPTZ, and marker boundaries are whole-day DATEs. Comparing a
    # timestamp directly against end_date would exclude any order on
    # end_date itself after midnight, since end_date is meant to be
    # inclusive of the whole day.
    result = await db.execute(
        update(Order)
        .where(
            Order.merchant_id == marker.merchant_id,
            func.date(Order.order_date) >= marker.start_date,
            func.date(Order.order_date) <= marker.end_date,
            Order.is_anomalous.is_(False),
        )
        .values(is_anomalous=True)
    )
    await db.commit()
    return result.rowcount


async def reflag_bank_transactions_for_marker(db: AsyncSession, marker: ContextualMarker) -> int:
    """Bank analog of `reflag_orders_for_marker` (task 1.25).
    `bank_transactions` has no merchant/user column of its own (that lives
    on the parent `accounts` row via `Account.user_id`, the same key
    ingestion's `write_canonical_bank_rows` already passes as
    `merchant_id`), so this scopes through a subquery on `accounts.id` for
    the marker's merchant_id instead of filtering BankTransaction directly.
    transaction_date is already a plain Date column, so no func.date(...)
    wrapping is needed here either."""
    account_ids_subq = select(Account.id).where(Account.user_id == marker.merchant_id).scalar_subquery()
    result = await db.execute(
        update(BankTransaction)
        .where(
            BankTransaction.account_id.in_(account_ids_subq),
            BankTransaction.transaction_date >= marker.start_date,
            BankTransaction.transaction_date <= marker.end_date,
            BankTransaction.is_anomalous.is_(False),
        )
        .values(is_anomalous=True)
    )
    await db.commit()
    return result.rowcount


async def create_contextual_marker(
    db: AsyncSession,
    merchant_id: uuid.UUID,
    analyzer_type: AnalyzerType,
    label: str,
    start_date: date,
    end_date: date,
    created_by: Optional[uuid.UUID] = None,
) -> ContextualMarker:
    """Creates the marker and immediately triggers the re-flag job — per
    spec, "re-flag existing records whenever a new marker is added" is a
    consequence of creation, not a separate manual step."""
    marker = ContextualMarker(
        id=uuid.uuid4(),
        merchant_id=merchant_id,
        analyzer_type=analyzer_type,
        label=label,
        start_date=start_date,
        end_date=end_date,
        created_by=created_by,
    )
    db.add(marker)
    await db.commit()

    if analyzer_type == AnalyzerType.ecommerce:
        await reflag_orders_for_marker(db, marker)
    elif analyzer_type == AnalyzerType.bank:
        await reflag_bank_transactions_for_marker(db, marker)

    return marker
