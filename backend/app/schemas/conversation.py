import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class SpeechSegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    speaker: str
    start: float
    end: float
    text: str


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agentId: uuid.UUID
    agentName: str
    projectId: uuid.UUID
    provider: Optional[str] = None
    externalId: Optional[str] = None
    score: Optional[int] = None
    grade: Optional[str] = None
    duration: str
    durationSec: int
    status: str
    date: str
    startedAt: Optional[str] = None
    endedAt: Optional[str] = None
    cost: Optional[float] = None
    audioUrl: Optional[str] = None
    latencyMs: Optional[int] = None
    interruptions: Optional[int] = None
    deadAirPercent: Optional[float] = None
    speechRateWpm: Optional[int] = None
    emotion: Optional[str] = None
    voiceQuality: Optional[int] = None
    customer: Optional[str] = None
    hasRecording: bool
    hasTranscript: bool
    emotionTimeline: List[str] = []
    detectedIssues: List[str] = []
    segments: List[SpeechSegmentResponse] = []
    interruptionDetails: Optional[dict] = None
    rawMetrics: Optional[dict] = None


class ConversationIngestRequest(BaseModel):
    projectId: Optional[uuid.UUID] = None
    provider: str
    providerCallId: str
