"""add 2fa fields to users

Revision ID: 5d1846ecff25
Revises: c4cc5987e2f5
Create Date: 2026-07-24 20:57:33.013228

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d1846ecff25'
down_revision: Union[str, Sequence[str], None] = 'c4cc5987e2f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('totp_secret', sa.String(), nullable=True))
    op.add_column('users', sa.Column('totp_enabled', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'totp_enabled')
    op.drop_column('users', 'totp_secret')
