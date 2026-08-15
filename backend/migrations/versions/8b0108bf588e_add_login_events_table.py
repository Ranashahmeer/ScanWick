"""add login events table

Revision ID: 8b0108bf588e
Revises: 76644bfd693d
Create Date: 2026-07-24 20:57:36.826683

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b0108bf588e'
down_revision: Union[str, Sequence[str], None] = '76644bfd693d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'login_events',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('result', sa.Enum('success', 'blocked', name='logineventresult'), nullable=False),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_login_events_user_id'), 'login_events', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_login_events_user_id'), table_name='login_events')
    op.drop_table('login_events')

    # Same reasoning as b3074bfe93d6's downgrade: op.create_table() implicitly
    # runs CREATE TYPE for the Enum column above; drop_table() doesn't drop
    # it, so it must be explicit, and only on Postgres (SQLite has no enum type).
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS logineventresult")
