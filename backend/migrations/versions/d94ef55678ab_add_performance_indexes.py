"""add_performance_indexes

Revision ID: d94ef55678ab
Revises: d84df4e634f7
Create Date: 2026-07-20 17:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd94ef55678ab'
down_revision: Union[str, Sequence[str], None] = 'd84df4e634f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('idx_conversations_project_created', 'conversations', ['project_id', 'created_at'], unique=False)
    op.create_index('idx_speech_segments_conv_start', 'speech_segments', ['conversation_id', 'start_sec'], unique=False)
    op.create_index('idx_agents_project_provider_ext', 'agents', ['project_id', 'provider', 'external_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_agents_project_provider_ext', table_name='agents')
    op.drop_index('idx_speech_segments_conv_start', table_name='speech_segments')
    op.drop_index('idx_conversations_project_created', table_name='conversations')
