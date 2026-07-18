import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import BaseModel

class AlertRule(BaseModel):
    __tablename__ = "alert_rules"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    metric = Column(String(50), nullable=False)
    threshold = Column(String(50), nullable=False)
    duration = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)

    project = relationship("Project", back_populates="alert_rules")
    alerts = relationship("Alert", back_populates="alert_rule", cascade="all, delete-orphan")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    alert_rule_id = Column(UUID(as_uuid=True), ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=False)  # e.g., 'Triggered', 'Recovered'
    triggered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="alerts")
    alert_rule = relationship("AlertRule", back_populates="alerts")
    conversation = relationship("Conversation", back_populates="alerts")
