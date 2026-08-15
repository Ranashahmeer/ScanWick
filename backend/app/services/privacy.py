import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Account,
    BankAccountIdentifier,
    BankTransaction,
    Order,
    OrderItem,
    ReconciliationReport,
    Upload,
)


async def delete_all_merchant_data(db: AsyncSession, user_id: int, merchant_id: uuid.UUID) -> None:
    """Privacy & Data > "Delete all data" — permanently wipes every uploaded
    dataset and everything derived from it for this merchant. Deliberately
    scoped to data only: the `users` row itself, subscription/billing
    history, and login/session records are untouched, so the account can
    keep using the product with a clean slate afterwards.

    Deletes in FK-safe order (children before parents). `Account.user_id` is
    really a merchant-scoped UUID despite the column name (see
    app/models/accounts.py's docstring) — same `merchant_id` as every other
    table here. `BankAccountIdentifier` is the one exception: it's scoped by
    the real integer `users.id` (a legacy table predating the merchant_id
    convention), not `merchant_id`.
    """
    account_ids = select(Account.id).where(Account.user_id == merchant_id)

    await db.execute(delete(OrderItem).where(OrderItem.merchant_id == merchant_id))
    await db.execute(delete(Order).where(Order.merchant_id == merchant_id))

    await db.execute(delete(BankTransaction).where(BankTransaction.account_id.in_(account_ids)))
    await db.execute(delete(Account).where(Account.user_id == merchant_id))

    await db.execute(delete(Upload).where(Upload.merchant_id == merchant_id))
    await db.execute(delete(ReconciliationReport).where(ReconciliationReport.merchant_id == merchant_id))

    await db.execute(delete(BankAccountIdentifier).where(BankAccountIdentifier.user_id == user_id))

    await db.commit()
