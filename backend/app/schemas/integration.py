from typing import Optional
from pydantic import BaseModel, ConfigDict

class IntegrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str  # lowercase provider key
    name: str  # e.g., 'Vapi'
    connected: bool
    apiKey: str
    webhookUrl: Optional[str] = None
    config: Optional[dict] = None
    lastSyncedAt: Optional[str] = None


class IntegrationUpdate(BaseModel):
    apiKey: Optional[str] = None
    webhookUrl: Optional[str] = None


class TestConnectionRequest(BaseModel):
    apiKey: str


class TestConnectionResponse(BaseModel):
    success: bool
    message: str


class SyncAgentsResponse(BaseModel):
    success: bool
    count: int
    message: str


class SyncCallsResponse(BaseModel):
    success: bool
    total: int
    imported: int
    skipped: int
    message: str
