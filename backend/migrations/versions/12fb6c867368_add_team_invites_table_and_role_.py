"""add team_invites table and role invite flag

Revision ID: 12fb6c867368
Revises: b3074bfe93d6
Create Date: 2026-07-22 09:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '12fb6c867368'
down_revision: Union[str, Sequence[str], None] = 'b3074bfe93d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('team_invites',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('merchant_id', sa.Uuid(), nullable=False),
    sa.Column('invited_by_user_id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    # `vertical` already exists as a Postgres enum type (created by the
    # user_merchant_roles migration) -- create_type=False reuses it instead
    # of trying (and failing) to CREATE TYPE vertical a second time. No-op
    # on SQLite, which has no enum type at all.
    sa.Column('vertical', sa.Enum('ecommerce', 'sales', 'bank', name='vertical', create_type=False), nullable=False),
    sa.Column('role', sa.String(), nullable=False),
    sa.Column('rep_id', sa.Uuid(), nullable=True),
    sa.Column('token', sa.String(), nullable=False),
    sa.Column('status', sa.Enum('pending', 'accepted', 'revoked', 'expired', name='teaminvitestatus'), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.ForeignKeyConstraint(['invited_by_user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token', name='uq_team_invites_token'),
    )
    op.create_index(op.f('ix_team_invites_merchant_id'), 'team_invites', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_team_invites_email'), 'team_invites', ['email'], unique=False)
    op.create_index(op.f('ix_team_invites_token'), 'team_invites', ['token'], unique=True)

    op.add_column('user_merchant_roles', sa.Column('granted_via_invite', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user_merchant_roles', 'granted_via_invite')

    op.drop_index(op.f('ix_team_invites_token'), table_name='team_invites')
    op.drop_index(op.f('ix_team_invites_email'), table_name='team_invites')
    op.drop_index(op.f('ix_team_invites_merchant_id'), table_name='team_invites')
    op.drop_table('team_invites')

    # Only drop the invite-status enum -- `vertical` is shared with
    # user_merchant_roles and must not be dropped here.
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS teaminvitestatus")
