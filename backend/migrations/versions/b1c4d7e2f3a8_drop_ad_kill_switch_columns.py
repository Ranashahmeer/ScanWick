"""drop ad_kill_switch columns from merchant_settings

Revision ID: b1c4d7e2f3a8
Revises: a3f7b6c9e1d2
Create Date: 2026-08-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c4d7e2f3a8'
down_revision: Union[str, Sequence[str], None] = 'a3f7b6c9e1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Section 4: the ad-kill-switch feature (ecommerce_ad_kill_switch.py,
    the /predictive/ad-kill-switch/* routes) is deleted -- these columns
    were baked into merchant_settings' original creation migration
    (a1842ad3c5c3), not a separately revertible one, so a real drop
    migration is needed rather than editing that historical file.
    """
    with op.batch_alter_table('merchant_settings') as batch_op:
        batch_op.drop_column('ad_kill_threshold_days')
        batch_op.drop_column('ad_kill_mode')

    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS adkillmode")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('merchant_settings') as batch_op:
        batch_op.add_column(
            sa.Column(
                'ad_kill_mode',
                sa.Enum('manual', 'auto', name='adkillmode'),
                nullable=False,
                server_default='manual',
            )
        )
        batch_op.add_column(
            sa.Column('ad_kill_threshold_days', sa.Integer(), nullable=False, server_default='7')
        )
