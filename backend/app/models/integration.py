from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Integration(BaseModel):
    __tablename__ = "integrations"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(50), nullable=False)
    connected = Column(Boolean, nullable=False, default=False)
    api_key = Column(String(500), nullable=True)
    webhook_url = Column(String(2048), nullable=True)
    config = Column(JSONB, nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="integrations")
