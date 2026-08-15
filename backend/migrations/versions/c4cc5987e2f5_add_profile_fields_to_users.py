"""add profile fields to users

Revision ID: c4cc5987e2f5
Revises: 3675a636ac70
Create Date: 2026-07-24 20:57:11.085428

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4cc5987e2f5'
down_revision: Union[str, Sequence[str], None] = '3675a636ac70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('company', sa.String(), nullable=True))
    op.add_column('users', sa.Column('company_size', sa.String(), nullable=True))
    op.add_column('users', sa.Column('industry', sa.String(), nullable=True))
    op.add_column('users', sa.Column('primary_currency', sa.String(), nullable=True))
    op.add_column('users', sa.Column('language', sa.String(), nullable=True))
    op.add_column('users', sa.Column('timezone', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'timezone')
    op.drop_column('users', 'language')
    op.drop_column('users', 'primary_currency')
    op.drop_column('users', 'industry')
    op.drop_column('users', 'company_size')
    op.drop_column('users', 'company')
