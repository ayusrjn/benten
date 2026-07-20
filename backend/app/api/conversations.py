from typing import List, Optional
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

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
    rawMetrics: Optional[dict] = None

    class Config:
        from_attributes = True

class ConversationIngestRequest(BaseModel):
    projectId: Optional[uuid.UUID] = None
    provider: str
    providerCallId: str

def format_duration(seconds: int) -> str:
    if not seconds:
        return "0s"
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    rem_seconds = seconds % 60
    if rem_seconds == 0:
        return f"{minutes}m"
    return f"{minutes}m {rem_seconds}s"

def calculate_grade(score: Optional[int]) -> Optional[str]:
    if score is None:
        return None
    if score >= 95:
        return "A+"
    elif score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    else:
        return "F"

def map_conversation_to_response(db: Session, c: Conversation) -> ConversationResponse:
    agent_name = "Unknown Agent"
    if c.agent:
        agent_name = c.agent.name

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

    date_str = c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else ""

    # Real detected issues calculation based strictly on existing metrics
    detected_issues = []
    if c.latency_ms and c.latency_ms > 1000:
        detected_issues.append(f"Average latency exceeded {c.latency_ms}ms")
    if c.dead_air_percent and c.dead_air_percent > 10.0:
        detected_issues.append(f"Dead air exceeded 10% ({c.dead_air_percent}%)")
    if c.interruptions and c.interruptions > 4:
        detected_issues.append(f"Frequent user interruptions count: {c.interruptions}")
    if c.primary_emotion in ["frustrated", "angry"]:
        detected_issues.append(f"User exhibited frustration markers")

    # Only include emotion timeline if real timeline data exists in raw metrics
    raw_meta = c.raw_metrics_json or {}
    emotion_timeline = raw_meta.get("emotion_timeline", [])

    # Customer identifier resolution (strictly real provider data)
    cust_val = (
        raw_meta.get("provider_metadata", {}).get("customer") or 
        raw_meta.get("customer") or 
        None
    )

    prov_val = c.provider or raw_meta.get("provider") or "vapi"
    ext_id_val = c.external_id or raw_meta.get("provider_call_id") or str(c.id)

    audio_url_val = c.audio_url
    if audio_url_val and audio_url_val.startswith("/static/"):
        audio_url_val = f"http://localhost:8000{audio_url_val}"

    return ConversationResponse(
        id=c.id,
        agentId=c.agent_id,
        agentName=agent_name,
        projectId=c.project_id,
        provider=prov_val,
        externalId=ext_id_val,
        score=c.health_score,
        grade=calculate_grade(c.health_score),
        duration=format_duration(c.duration_sec or 0),
        durationSec=c.duration_sec or 0,
        status=c.status or "Completed",
        date=date_str,
        startedAt=c.started_at.isoformat() if c.started_at else None,
        endedAt=c.ended_at.isoformat() if c.ended_at else None,
        cost=float(c.cost) if c.cost is not None else None,
        audioUrl=audio_url_val,
        latencyMs=c.latency_ms,
        interruptions=c.interruptions,
        deadAirPercent=float(c.dead_air_percent) if c.dead_air_percent is not None else None,
        speechRateWpm=c.speech_rate_wpm,
        emotion=c.primary_emotion,
        voiceQuality=c.voice_quality,
        customer=cust_val,
        hasRecording=bool(c.audio_url),
        hasTranscript=len(segments) > 0,
        emotionTimeline=emotion_timeline,
        detectedIssues=detected_issues,
        segments=segment_responses,
        rawMetrics=raw_meta
    )

@router.get("", response_model=List[ConversationResponse])
def list_conversations(
    response: Response,
    projectId: Optional[uuid.UUID] = None,
    agentId: Optional[uuid.UUID] = None,
    provider: Optional[str] = None,
    status: Optional[str] = None,
    grade: Optional[str] = None,
    minScore: Optional[int] = None,
    maxScore: Optional[int] = None,
    minDuration: Optional[int] = None,
    maxDuration: Optional[int] = None,
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

    # Filter by Provider
    if provider and provider.lower() != "all":
        query = query.filter(Conversation.provider.ilike(provider.lower()))

    # Filter by Status
    if status and status.lower() != "all":
        query = query.filter(Conversation.status.ilike(status))

    # Filter by Grade / Score
    if grade:
        g = grade.upper()
        if g in ("A+", "A"):
            query = query.filter(Conversation.health_score >= 90)
        elif g == "B":
            query = query.filter(Conversation.health_score >= 80, Conversation.health_score < 90)
        elif g == "C":
            query = query.filter(Conversation.health_score >= 70, Conversation.health_score < 80)
        elif g == "F":
            query = query.filter(Conversation.health_score < 70)

    if minScore is not None:
        query = query.filter(Conversation.health_score >= minScore)

    if maxScore is not None:
        query = query.filter(Conversation.health_score <= maxScore)

    # Filter by Duration
    if minDuration is not None:
        query = query.filter(Conversation.duration_sec >= minDuration)

    if maxDuration is not None:
        query = query.filter(Conversation.duration_sec <= maxDuration)

    # Filter by Max Latency
    if maxLatency is not None:
        query = query.filter(Conversation.latency_ms <= maxLatency)

    # Multi-field search
    if q:
        query = query.outerjoin(Agent).filter(
            or_(
                Agent.name.ilike(f"%{q}%"),
                Conversation.provider.ilike(f"%{q}%"),
                Conversation.external_id.ilike(f"%{q}%"),
                Conversation.id.cast(func.text).ilike(f"%{q}%")
            )
        )

    # Sorting
    if _sort:
        col = None
        if _sort in ("score", "health_score"):
            col = Conversation.health_score
        elif _sort in ("duration", "duration_sec"):
            col = Conversation.duration_sec
        elif _sort in ("date", "created_at"):
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

@router.post("/{id}/reevaluate", status_code=status.HTTP_202_ACCEPTED)
def reevaluate_conversation(
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

    from app.workers.tasks import evaluate_audio
    c.status = "Processing"
    db.commit()

    task = evaluate_audio.delay(str(c.id), c.audio_url or "")
    return {
        "status": "Submitted",
        "taskId": task.id,
        "message": f"Re-evaluation background task queued for call {id}"
    }

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

