import uuid
from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, Text, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    external_id = Column(String(255), index=True, nullable=True)
    provider = Column(String(50), index=True, nullable=True)
    duration_sec = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    cost = Column(Numeric(10, 4), nullable=True)
    status = Column(String(20), nullable=False)  # e.g., 'Processing', 'Completed', 'Error', 'Healthy', 'Warning', 'Critical'
    health_score = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=False, default=0)
    dead_air_percent = Column(Numeric(5, 2), nullable=False, default=0.00)
    interruptions = Column(Integer, nullable=False, default=0)
    speech_rate_wpm = Column(Integer, nullable=False, default=0)
    primary_emotion = Column(String(50), nullable=True)
    voice_quality = Column(Integer, nullable=True)
    audio_url = Column(String(2048), nullable=True)
    raw_metrics_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint('health_score >= 0 AND health_score <= 100', name='check_health_score_range'),
        CheckConstraint('voice_quality >= 0 AND voice_quality <= 100', name='check_voice_quality_range'),
    )

    project = relationship("Project", back_populates="conversations")
    agent = relationship("Agent", back_populates="conversations")
    speech_segments = relationship("SpeechSegment", back_populates="conversation", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="conversation")


class SpeechSegment(Base):
    __tablename__ = "speech_segments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    speaker = Column(String(10), nullable=False)
    start_sec = Column(Numeric(6, 2), nullable=False)
    end_sec = Column(Numeric(6, 2), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), primary_key=True, server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("speaker IN ('user', 'agent')", name="check_speaker_type"),
    )

    conversation = relationship("Conversation", back_populates="speech_segments")
