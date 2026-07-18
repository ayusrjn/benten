import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import BaseModel

class Organization(BaseModel):
    __tablename__ = "organizations"

    name = Column(String(255), nullable=False)

    projects = relationship("Project", back_populates="organization", cascade="all, delete-orphan")
    members = relationship("Member", back_populates="organization", cascade="all, delete-orphan")


class Member(Base):
    __tablename__ = "members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    role = Column(String(50), nullable=False)
    avatar_url = Column(String(2048), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    organization = relationship("Organization", back_populates="members")
