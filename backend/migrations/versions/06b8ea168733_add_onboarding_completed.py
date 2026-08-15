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
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'users' not in tables:
        op.create_table(
            'users',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=False),
            sa.Column('hashed_password', sa.String(length=255), nullable=False),
            sa.Column('full_name', sa.String(length=255), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('onboarding_completed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    else:
        columns = [c['name'] for c in inspector.get_columns('users')]
        if 'onboarding_completed' not in columns:
            op.add_column('users', sa.Column('onboarding_completed', sa.Boolean(), nullable=False, server_default=sa.text('false')))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if 'users' in tables:
        columns = [c['name'] for c in inspector.get_columns('users')]
        if 'onboarding_completed' in columns:
            op.drop_column('users', 'onboarding_completed')
