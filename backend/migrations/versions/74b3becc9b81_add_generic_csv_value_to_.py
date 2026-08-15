"""add generic_csv value to orderdatasource enum

Revision ID: 74b3becc9b81
Revises: a565fc6d6ec5
Create Date: 2026-07-06 15:25:33.156348

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '74b3becc9b81'
down_revision: Union[str, Sequence[str], None] = 'a565fc6d6ec5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Only Postgres needs anything here: sa.Enum has no native backing on
    # SQLite in this project (create_constraint defaults to False for
    # non-native-enum dialects -- confirmed directly against the raw
    # sqlite_master DDL, which shows no CHECK constraint on this column at
    # all), so a new Python-side enum value is already usable there with no
    # schema change. Postgres's `orderdatasource` is a real native ENUM type
    # and does need the new value added explicitly.
    if op.get_bind().dialect.name == "postgresql":
        # ALTER TYPE ... ADD VALUE cannot run inside the transaction Alembic
        # normally wraps migrations in -- autocommit_block() runs it outside
        # that transaction instead, which Postgres requires for this command.
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE orderdatasource ADD VALUE IF NOT EXISTS 'generic_csv'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres has no native "remove enum value" operation -- any 'generic_csv'
    # rows would need to be migrated/deleted first, which this system has no
    # basis for deciding automatically, so this is intentionally a no-op.
    # Nothing to undo on SQLite for the same reason nothing was done above.
