"""add subscriptions and payment_transactions tables

Revision ID: b3074bfe93d6
Revises: 3135dec86355
Create Date: 2026-07-22 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3074bfe93d6'
down_revision: Union[str, Sequence[str], None] = '3135dec86355'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('subscriptions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('provider', sa.String(), nullable=False),
    sa.Column('tier', sa.String(), nullable=False, server_default='basic'),
    sa.Column('status', sa.Enum('active', 'past_due', 'cancelled', 'incomplete', name='subscriptionstatus'), nullable=False),
    sa.Column('provider_customer_code', sa.String(), nullable=True),
    sa.Column('provider_subscription_code', sa.String(), nullable=True),
    sa.Column('provider_subscription_token', sa.String(), nullable=True),
    sa.Column('provider_plan_code', sa.String(), nullable=True),
    sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
    sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False, server_default='false'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', name='uq_subscriptions_user_id'),
    )
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=True)

    op.create_table('payment_transactions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('subscription_id', sa.Uuid(), nullable=True),
    sa.Column('provider', sa.String(), nullable=False),
    sa.Column('provider_reference', sa.String(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('currency', sa.String(), nullable=False, server_default='NGN'),
    sa.Column('status', sa.Enum('pending', 'success', 'failed', name='paymenttransactionstatus'), nullable=False),
    sa.Column('provider_event_type', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('provider_reference', name='uq_payment_transactions_provider_reference'),
    )
    op.create_index(op.f('ix_payment_transactions_user_id'), 'payment_transactions', ['user_id'], unique=False)
    op.create_index(op.f('ix_payment_transactions_provider_reference'), 'payment_transactions', ['provider_reference'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_payment_transactions_provider_reference'), table_name='payment_transactions')
    op.drop_index(op.f('ix_payment_transactions_user_id'), table_name='payment_transactions')
    op.drop_table('payment_transactions')

    op.drop_index(op.f('ix_subscriptions_user_id'), table_name='subscriptions')
    op.drop_table('subscriptions')

    # op.create_table() implicitly runs CREATE TYPE for the two status enum
    # columns above, but op.drop_table() doesn't drop them -- must be
    # explicit, and only on Postgres (SQLite has no enum type at all).
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS paymenttransactionstatus")
        op.execute("DROP TYPE IF EXISTS subscriptionstatus")
