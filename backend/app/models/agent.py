from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Agent(BaseModel):
    __tablename__ = "agents"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    provider = Column(String(50), nullable=False)

    project = relationship("Project", back_populates="agents")
    conversations = relationship("Conversation", back_populates="agent", cascade="all, delete-orphan")
