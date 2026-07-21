import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict

class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    projectId: uuid.UUID
    name: str
    provider: str
    externalId: Optional[str] = None
    description: Optional[str] = None
    lastSyncedAt: Optional[str] = None
    rawMetadata: Optional[Dict[str, Any]] = None
    conversationsCount: int
    healthScore: int
    latencyTrend: List[int]
    deadAirTrend: List[float]
    interruptionsTrend: List[int]
    emotionTrend: List[int]
    topProblems: List[str]


class AgentCreate(BaseModel):
    projectId: Optional[uuid.UUID] = None
    name: str
    provider: str
    externalId: Optional[str] = None
    description: Optional[str] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    description: Optional[str] = None


class GlobalSyncAgentsResponse(BaseModel):
    success: bool
    totalSynced: int
    message: str
