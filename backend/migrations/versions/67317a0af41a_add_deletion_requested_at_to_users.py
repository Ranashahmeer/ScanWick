"""add deletion requested at to users

Revision ID: 67317a0af41a
Revises: 5d1846ecff25
Create Date: 2026-07-24 20:57:34.329285

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '67317a0af41a'
down_revision: Union[str, Sequence[str], None] = '5d1846ecff25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('deletion_requested_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'deletion_requested_at')
