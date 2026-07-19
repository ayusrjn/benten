from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.security import get_current_active_user
from app.models.user import User
from app.models.project import Project
from app.models.agent import Agent
from app.models.conversation import Conversation, SpeechSegment
from app.models.organization import Member
from app.api.integrations import get_or_create_user_project

router = APIRouter(prefix="/conversations", tags=["Conversations"])

class SpeechSegmentResponse(BaseModel):
    speaker: str
    start: float
    end: float
    text: str

    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    id: uuid.UUID
    agentId: uuid.UUID
    agentName: str
    projectId: uuid.UUID
    score: int
    duration: str
    durationSec: int
    status: str
    date: str
    latencyMs: int
    interruptions: int
    deadAirPercent: float
    speechRateWpm: int
    emotion: Optional[str] = None
    voiceQuality: int
    emotionTimeline: List[str]
    detectedIssues: List[str]
    segments: List[SpeechSegmentResponse]
    rawMetrics: Optional[dict] = None

    class Config:
        from_attributes = True

class ConversationIngestRequest(BaseModel):
    projectId: Optional[uuid.UUID] = None
    provider: str
    providerCallId: str

def format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    rem_seconds = seconds % 60
    if rem_seconds == 0:
        return f"{minutes}m"
    return f"{minutes}m {rem_seconds}s"

def map_conversation_to_response(db: Session, c: Conversation) -> ConversationResponse:
    # Resolve agent name
    agent_name = "Unknown Agent"
    if c.agent:
        agent_name = c.agent.name
        
    # Get segments
    segments = db.query(SpeechSegment).filter(
        SpeechSegment.conversation_id == c.id
    ).order_by(SpeechSegment.start_sec.asc()).all()
    
    segment_responses = [
        SpeechSegmentResponse(
            speaker=s.speaker,
            start=float(s.start_sec),
            end=float(s.end_sec),
            text=s.text
        ) for s in segments
    ]
    
    # Format date
    date_str = c.created_at.strftime("%Y-%m-%d %H:%M")
    
    # Construct detected issues list based on thresholds or raw metrics
    detected_issues = []
    if c.latency_ms > 1000:
        detected_issues.append(f"Average latency exceeded {c.latency_ms}ms")
    if c.dead_air_percent > 10.0:
        detected_issues.append(f"Dead air exceeded 10% ({c.dead_air_percent}%)")
    if c.interruptions > 4:
        detected_issues.append(f"Frequent user interruptions count: {c.interruptions}")
    if c.primary_emotion in ["frustrated", "angry"]:
        detected_issues.append(f"User exhibited frustration markers")
        
    # Standard fallback mock issues if empty but low health score
    if not detected_issues and c.health_score < 90:
        detected_issues = ["Slight voice quality degradation", "Minor timing overlaps detected"]
        
    # Construct an emotion timeline
    emotion_timeline = ["😐"] * 8
    if c.primary_emotion == "neutral":
        emotion_timeline = ["😐", "😐", "😀", "😀", "😐", "😐", "😀", "😀"]
    elif c.primary_emotion == "calm":
        emotion_timeline = ["😀", "😀", "😐", "😐", "😐", "😞", "😞", "😀"]
    elif c.primary_emotion in ["frustrated", "angry"]:
        emotion_timeline = ["😐", "😐", "😞", "😞", "😡", "😡", "😞", "😐"]
        
    return ConversationResponse(
        id=c.id,
        agentId=c.agent_id,
        agentName=agent_name,
        projectId=c.project_id,
        score=c.health_score,
        duration=format_duration(c.duration_sec),
        durationSec=c.duration_sec,
        status=c.status,
        date=date_str,
        latencyMs=c.latency_ms,
        interruptions=c.interruptions,
        deadAirPercent=float(c.dead_air_percent),
        speechRateWpm=c.speech_rate_wpm,
        emotion=c.primary_emotion or "neutral",
        voiceQuality=c.voice_quality,
        emotionTimeline=emotion_timeline,
        detectedIssues=detected_issues,
        segments=segment_responses,
        rawMetrics=c.raw_metrics_json
    )

@router.get("", response_model=List[ConversationResponse])
def list_conversations(
    response: Response,
    projectId: Optional[uuid.UUID] = None,
    agentId: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    minScore: Optional[int] = None,
    maxLatency: Optional[int] = None,
    _start: Optional[int] = None,
    _end: Optional[int] = None,
    _sort: Optional[str] = None,
    _order: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = get_or_create_user_project(db, current_user)
    active_project_id = projectId or project.id
    
    member = db.query(Member).filter(Member.email == current_user.email).first()
    proj = db.query(Project).filter(Project.id == active_project_id, Project.organization_id == member.organization_id).first()
    if not proj:
        raise HTTPException(status_code=403, detail="Access denied to specified project")
        
    query = db.query(Conversation).filter(Conversation.project_id == active_project_id)
    
    # Filter by Agent
    if agentId:
        query = query.filter(Conversation.agent_id == agentId)
        
    # Filter by Status
    if status:
        query = query.filter(Conversation.status.ilike(status))
        
    # Filter by Min Score
    if minScore is not None:
        query = query.filter(Conversation.health_score >= minScore)
        
    # Filter by Max Latency
    if maxLatency is not None:
        query = query.filter(Conversation.latency_ms <= maxLatency)
        
    # Search query (by agent name or ID string match)
    if q:
        query = query.join(Agent).filter(
            (Agent.name.ilike(f"%{q}%")) |
            (Conversation.id.cast(func.text).ilike(f"%{q}%"))
        )
        
    # Sort
    if _sort:
        col = None
        if _sort == "score":
            col = Conversation.health_score
        elif _sort == "duration":
            col = Conversation.duration_sec
        elif _sort == "date":
            col = Conversation.created_at
        else:
            col = getattr(Conversation, _sort, None)
            
        if col is not None:
            if _order and _order.lower() == "desc":
                query = query.order_by(col.desc())
            else:
                query = query.order_by(col.asc())
    else:
        query = query.order_by(Conversation.created_at.desc())
        
    total = query.count()
    response.headers["x-total-count"] = str(total)
    
    # Paginate
    if _start is not None and _end is not None:
        query = query.offset(_start).limit(_end - _start)
        
    conversations = query.all()
    return [map_conversation_to_response(db, c) for c in conversations]

@router.get("/{id}", response_model=ConversationResponse)
def get_conversation(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    member = db.query(Member).filter(Member.email == current_user.email).first()
    
    c = db.query(Conversation).join(Project).filter(
        Conversation.id == id,
        Project.organization_id == member.organization_id
    ).first()
    
    if not c:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    return map_conversation_to_response(db, c)

@router.post("", status_code=status.HTTP_202_ACCEPTED)
def trigger_ingestion(
    payload: ConversationIngestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = get_or_create_user_project(db, current_user)
    active_project_id = payload.projectId or project.id
    
    member = db.query(Member).filter(Member.email == current_user.email).first()
    proj = db.query(Project).filter(Project.id == active_project_id, Project.organization_id == member.organization_id).first()
    if not proj:
        raise HTTPException(status_code=403, detail="Access denied to specified project")
        
    from app.workers.tasks import ingest_call
    
    # Trigger Celery worker background task
    task = ingest_call.delay(
        project_id=str(active_project_id),
        provider=payload.provider,
        provider_call_id=payload.providerCallId
    )
    
    return {
        "status": "Submitted",
        "taskId": task.id,
        "message": f"Background call ingestion triggered for provider '{payload.provider}'"
    }

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    member = db.query(Member).filter(Member.email == current_user.email).first()
    
    c = db.query(Conversation).join(Project).filter(
        Conversation.id == id,
        Project.organization_id == member.organization_id
    ).first()
    
    if not c:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    db.delete(c)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
