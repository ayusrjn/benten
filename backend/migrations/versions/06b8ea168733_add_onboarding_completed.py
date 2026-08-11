"""add_onboarding_completed

Revision ID: 06b8ea168733
Revises: d94ef55678ab
Create Date: 2026-08-11 14:38:14.622341

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '06b8ea168733'
down_revision: Union[str, Sequence[str], None] = 'd94ef55678ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('onboarding_completed', sa.Boolean(), nullable=False, server_default=sa.text('false')))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'onboarding_completed')
