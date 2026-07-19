from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Agent(BaseModel):
    __tablename__ = "agents"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    provider = Column(String(50), nullable=False)
    external_id = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    raw_metadata = Column(JSONB, nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="agents")
    conversations = relationship("Conversation", back_populates="agent", cascade="all, delete-orphan")

