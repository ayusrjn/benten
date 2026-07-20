"""add_call_sync_columns

Revision ID: d84df4e634f7
Revises: c73ce3d523e6
Create Date: 2026-07-20 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd84df4e634f7'
down_revision: Union[str, Sequence[str], None] = 'b28490a1f092'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to conversations
    op.add_column('conversations', sa.Column('external_id', sa.String(length=255), nullable=True))
    op.add_column('conversations', sa.Column('provider', sa.String(length=50), nullable=True))
    op.add_column('conversations', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('conversations', sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('conversations', sa.Column('cost', sa.Numeric(precision=10, scale=4), nullable=True))
    
    op.create_index(op.f('ix_conversations_external_id'), 'conversations', ['external_id'], unique=False)
    op.create_index(op.f('ix_conversations_provider'), 'conversations', ['provider'], unique=False)
    op.create_index('idx_conversations_provider_ext_id', 'conversations', ['provider', 'external_id'], unique=False)

    # Add last_synced_at to integrations
    op.add_column('integrations', sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('integrations', 'last_synced_at')
    
    op.drop_index('idx_conversations_provider_ext_id', table_name='conversations')
    op.drop_index(op.f('ix_conversations_provider'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_external_id'), table_name='conversations')
    
    op.drop_column('conversations', 'cost')
    op.drop_column('conversations', 'ended_at')
    op.drop_column('conversations', 'started_at')
    op.drop_column('conversations', 'provider')
    op.drop_column('conversations', 'external_id')
