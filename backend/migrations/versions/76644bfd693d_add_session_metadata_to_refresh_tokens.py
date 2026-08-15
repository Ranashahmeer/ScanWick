"""add session metadata to refresh tokens

Revision ID: 76644bfd693d
Revises: 67317a0af41a
Create Date: 2026-07-24 20:57:35.572975

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76644bfd693d'
down_revision: Union[str, Sequence[str], None] = '67317a0af41a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('refresh_tokens', sa.Column('user_agent', sa.String(), nullable=True))
    op.add_column('refresh_tokens', sa.Column('ip_address', sa.String(), nullable=True))
    op.add_column('refresh_tokens', sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('refresh_tokens', 'last_used_at')
    op.drop_column('refresh_tokens', 'ip_address')
    op.drop_column('refresh_tokens', 'user_agent')
