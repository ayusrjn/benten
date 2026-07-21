import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict

class AlertRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    metric: str
    threshold: str
    duration: str
    action: str


class AlertRuleCreate(BaseModel):
    projectId: Optional[uuid.UUID] = None
    metric: str
    threshold: str
    duration: str
    action: str


class AlertRuleUpdate(BaseModel):
    metric: Optional[str] = None
    threshold: Optional[str] = None
    duration: Optional[str] = None
    action: Optional[str] = None


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    status: str
    agentName: str
    timeText: str
    metric: str
