"""add orders unique constraint for 3.6 dedup

Revision ID: a3f7b6c9e1d2
Revises: f9e588f83fa9
Create Date: 2026-08-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f7b6c9e1d2'
down_revision: Union[str, Sequence[str], None] = 'f9e588f83fa9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    3.6: adds the DB-level backstop for ecommerce order deduplication
    (application-level dedup lives in ecommerce_ingestion.py's
    `write_canonical_rows`/`_generate_surrogate_external_id`). If this
    fails on an existing database because duplicate
    (merchant_id, data_source, external_order_id) rows already exist,
    those rows must be de-duplicated manually before re-running this
    migration -- see Section 8 of the developer scope guide (backup +
    rollback plan before any destructive/constraint-adding change).

    batch_alter_table, not a bare op.create_unique_constraint: SQLite has no
    real ALTER TABLE ... ADD CONSTRAINT, so this needs Alembic's
    recreate-table batch mode there (same reasoning as
    3675a636ac70_add_free_tier_and_payment_transaction_.py). A plain
    op.create_unique_constraint would work on Postgres alone but fail on
    SQLite (this project's dev/test DB).
    """
    with op.batch_alter_table("orders") as batch_op:
        batch_op.create_unique_constraint(
            "uq_orders_merchant_source_external_id",
            ["merchant_id", "data_source", "external_order_id"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_constraint("uq_orders_merchant_source_external_id", type_="unique")
