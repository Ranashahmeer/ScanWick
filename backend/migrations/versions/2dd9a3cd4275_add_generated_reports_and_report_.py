"""add generated_reports and report_schedules tables

Revision ID: 2dd9a3cd4275
Revises: f51f5c94d517
Create Date: 2026-07-26 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2dd9a3cd4275'
down_revision: Union[str, Sequence[str], None] = 'f51f5c94d517'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'generated_reports',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('merchant_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column(
            'module',
            sa.Enum('finance', 'sales', 'commerce', 'cross_module', name='reportmodule'),
            nullable=False,
        ),
        sa.Column('template_key', sa.String(), nullable=True),
        sa.Column('date_range_start', sa.Date(), nullable=True),
        sa.Column('date_range_end', sa.Date(), nullable=True),
        sa.Column('stats', sa.JSON(), nullable=False),
        sa.Column('chart', sa.JSON(), nullable=False),
        sa.Column('note', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('pdf_url', sa.String(), nullable=True),
        sa.Column('excel_url', sa.String(), nullable=True),
        sa.Column('analysis_run_id', sa.Uuid(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_generated_reports_merchant_id'), 'generated_reports', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_generated_reports_template_key'), 'generated_reports', ['template_key'], unique=False)

    op.create_table(
        'report_schedules',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('merchant_id', sa.Uuid(), nullable=False),
        sa.Column('template_key', sa.String(), nullable=False),
        sa.Column(
            'frequency',
            sa.Enum('daily', 'weekly', 'monthly', 'quarterly', name='reportfrequency'),
            nullable=False,
        ),
        sa.Column('recipients', sa.String(), nullable=False),
        sa.Column('format', sa.Enum('pdf', 'excel', name='reportformat'), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_report_schedules_merchant_id'), 'report_schedules', ['merchant_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_report_schedules_merchant_id'), table_name='report_schedules')
    op.drop_table('report_schedules')

    op.drop_index(op.f('ix_generated_reports_template_key'), table_name='generated_reports')
    op.drop_index(op.f('ix_generated_reports_merchant_id'), table_name='generated_reports')
    op.drop_table('generated_reports')

    # op.create_table() implicitly runs CREATE TYPE for each Enum column
    # above; drop_table() doesn't drop them -- must be explicit, and only
    # on Postgres (SQLite has no enum type at all). Same reasoning as
    # 8b0108bf588e's downgrade.
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS reportformat")
        op.execute("DROP TYPE IF EXISTS reportfrequency")
        op.execute("DROP TYPE IF EXISTS reportmodule")
