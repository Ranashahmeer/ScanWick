"""add column_mappings table

Revision ID: b435471383cc
Revises: 2dd9a3cd4275
Create Date: 2026-07-27 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b435471383cc'
down_revision: Union[str, Sequence[str], None] = '2dd9a3cd4275'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'column_mappings',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('merchant_id', sa.Uuid(), nullable=False),
        sa.Column(
            'analyzer_type',
            sa.Enum('ecommerce', 'sales', 'bank', name='analyzertype', create_type=False),
            nullable=False,
        ),
        sa.Column('source_signature', sa.String(), nullable=False),
        sa.Column('mapping', sa.JSON(), nullable=False),
        sa.Column('unmapped_headers', sa.JSON(), nullable=True),
        sa.Column('value_rules', sa.JSON(), nullable=True),
        sa.Column('confirmed_by', sa.Integer(), nullable=True),
        sa.Column('confidence_summary', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'merchant_id', 'analyzer_type', 'source_signature', name='uq_column_mapping_signature'
        ),
    )
    op.create_index(op.f('ix_column_mappings_merchant_id'), 'column_mappings', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_column_mappings_source_signature'), 'column_mappings', ['source_signature'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_column_mappings_source_signature'), table_name='column_mappings')
    op.drop_index(op.f('ix_column_mappings_merchant_id'), table_name='column_mappings')
    op.drop_table('column_mappings')
    # `analyzertype` is create_type=False here (reusing the enum already
    # created by an earlier migration, e.g. 6aad96943bb2's
    # reconciliation_reports table) -- it must NOT be dropped by this
    # migration's downgrade, since other tables still depend on it.
