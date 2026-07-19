"""add_agent_sync_fields

Revision ID: b28490a1f092
Revises: c73ce3d523e6
Create Date: 2026-07-20 01:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b28490a1f092'
down_revision: Union[str, Sequence[str], None] = 'c73ce3d523e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('agents', sa.Column('external_id', sa.String(length=255), nullable=True))
    op.add_column('agents', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('agents', sa.Column('raw_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('agents', sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('agents', 'last_synced_at')
    op.drop_column('agents', 'raw_metadata')
    op.drop_column('agents', 'description')
    op.drop_column('agents', 'external_id')
