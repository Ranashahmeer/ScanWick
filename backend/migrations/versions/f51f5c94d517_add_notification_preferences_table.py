"""add notification preferences table

Revision ID: f51f5c94d517
Revises: 8b0108bf588e
Create Date: 2026-07-24 20:57:38.038833

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f51f5c94d517'
down_revision: Union[str, Sequence[str], None] = '8b0108bf588e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'notification_preferences',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('event_key', sa.String(), nullable=False),
        sa.Column('channel', sa.String(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'user_id', 'event_key', 'channel', name='uq_notification_pref_user_event_channel'
        ),
    )
    op.create_index(
        op.f('ix_notification_preferences_user_id'), 'notification_preferences', ['user_id'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_notification_preferences_user_id'), table_name='notification_preferences')
    op.drop_table('notification_preferences')
