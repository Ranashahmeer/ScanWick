"""add needs_mapping value to uploadstatus enum

Revision ID: f9e588f83fa9
Revises: b435471383cc
Create Date: 2026-07-27 16:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9e588f83fa9'
down_revision: Union[str, Sequence[str], None] = 'b435471383cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Same reasoning as 74b3becc9b81 (orderdatasource): sa.Enum has no
    # native backing on SQLite in this project, so a new Python-side value
    # is already usable there with no schema change. Postgres's
    # `uploadstatus` is a real native ENUM type and needs it added explicitly.
    if op.get_bind().dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE uploadstatus ADD VALUE IF NOT EXISTS 'needs_mapping'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres has no native "remove enum value" operation -- any
    # 'needs_mapping' rows would need to be migrated/deleted first, which
    # this system has no basis for deciding automatically, so this is
    # intentionally a no-op. Nothing to undo on SQLite for the same reason
    # nothing was done above.
