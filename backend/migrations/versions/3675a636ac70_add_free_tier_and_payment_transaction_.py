"""add free tier and payment_transaction tier column

Revision ID: 3675a636ac70
Revises: 12fb6c867368
Create Date: 2026-07-23 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3675a636ac70'
down_revision: Union[str, Sequence[str], None] = '12fb6c867368'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # batch_alter_table, not a bare op.alter_column: SQLite has no real
    # ALTER COLUMN ... SET DEFAULT support, so this needs Alembic's
    # recreate-table batch mode there. A plain op.alter_column would work
    # fine on Postgres alone but fail on SQLite (this project's dev/test DB).
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('subscription_tier', server_default='free')

    # "basic" used to mean "the unpaid default" (task 5.6's original
    # two-tier design). Now that Basic is a genuinely separate paid plan
    # (Free/Basic/Premium), every account that never actually paid for
    # anything must land on the real free tier instead of grandfathering
    # into paid-Basic access for nothing.
    op.execute("UPDATE users SET subscription_tier = 'free' WHERE subscription_tier = 'basic'")

    op.add_column('payment_transactions', sa.Column('tier', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('payment_transactions', 'tier')

    # Not reverting the 'basic' -> 'free' data migration: there is no way
    # to distinguish an account that was originally 'basic' (pre-migration)
    # from one that is genuinely 'free' post-migration by this point --
    # rewriting it back would be a guess, not a real reversal.
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('subscription_tier', server_default='basic')
