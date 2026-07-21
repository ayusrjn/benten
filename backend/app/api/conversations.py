from typing import List, Optional
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.security import get_current_active_user
from app.models.user import User
from app.models.project import Project
from app.models.conversation import Conversation, SpeechSegment
from app.models.organization import Member
from app.services.project_service import ProjectService
from app.services.conversation_service import ConversationService, format_duration, calculate_grade

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
    interruptionDetails: Optional[dict] = None
    rawMetrics: Optional[dict] = None

    class Config:
        from_attributes = True


class ConversationIngestRequest(BaseModel):
    projectId: Optional[uuid.UUID] = None
    provider: str
    providerCallId: str


def map_conversation_to_response(db: Session, c: Conversation) -> ConversationResponse:
    agent_name = c.agent.name if c.agent else "Unknown Agent"

    # Use pre-loaded speech_segments if available via joinedload (avoids N+1 query)
    segments = c.speech_segments if c.speech_segments is not None else db.query(SpeechSegment).filter(
        SpeechSegment.conversation_id == c.id
    ).order_by(SpeechSegment.start_sec.asc()).all()

    sorted_segments = sorted(segments, key=lambda s: float(s.start_sec))

    segment_responses = [
        SpeechSegmentResponse(
            speaker=s.speaker,
            start=float(s.start_sec),
            end=float(s.end_sec),
            text=s.text
        ) for s in sorted_segments
    ]

    date_str = c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else ""

    # Real detected issues calculation based strictly on metrics
    detected_issues = []
    if c.latency_ms and c.latency_ms > 1000:
        detected_issues.append(f"Average latency exceeded {c.latency_ms}ms")
    if c.dead_air_percent and c.dead_air_percent > 10.0:
        detected_issues.append(f"Dead air exceeded 10% ({c.dead_air_percent}%)")
    if c.interruptions and c.interruptions > 4:
        detected_issues.append(f"Frequent user interruptions count: {c.interruptions}")
    if c.primary_emotion in ["frustrated", "angry"]:
        detected_issues.append(f"User exhibited frustration markers")

    raw_meta = c.raw_metrics_json or {}
    emotion_timeline = raw_meta.get("emotion_timeline", [])

    interruption_details = raw_meta.get("interruption_details")
    if not interruption_details and sorted_segments:
        from app.pipeline.extractors import calculate_detailed_interruptions
        seg_dicts = [
            {"start": float(s.start_sec), "end": float(s.end_sec), "role": s.speaker}
            for s in sorted_segments
        ]
        interruption_details = calculate_detailed_interruptions(seg_dicts, float(c.duration_sec or 0))

    if interruption_details and "interruption_details" not in raw_meta:
        raw_meta = {**raw_meta, "interruption_details": interruption_details}

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
        hasTranscript=len(sorted_segments) > 0,
        emotionTimeline=emotion_timeline,
        detectedIssues=detected_issues,
        segments=segment_responses,
        interruptionDetails=interruption_details,
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
    project = ProjectService.get_or_create_user_project(db, current_user)
    active_project_id = projectId or project.id

    member = ProjectService.get_user_member(db, current_user)
    proj = db.query(Project).filter(Project.id == active_project_id, Project.organization_id == member.organization_id).first()
    if not proj:
        raise HTTPException(status_code=403, detail="Access denied to specified project")

    conversations, total = ConversationService.list_conversations(
        db=db,
        project_id=active_project_id,
        agent_id=agentId,
        provider=provider,
        status=status,
        grade=grade,
        min_score=minScore,
        max_score=maxScore,
        min_duration=minDuration,
        max_duration=maxDuration,
        max_latency=maxLatency,
        start=_start,
        end=_end,
        sort=_sort,
        order=_order,
        q=q
    )

    response.headers["x-total-count"] = str(total)
    return [map_conversation_to_response(db, c) for c in conversations]


@router.get("/{id}", response_model=ConversationResponse)
def get_conversation(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    member = ProjectService.get_user_member(db, current_user)
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")

    c = ConversationService.get_conversation_with_relations(db, conversation_id=id)
    if not c:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Verify organization authorization
    if c.project and c.project.organization_id != member.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return map_conversation_to_response(db, c)


@router.post("/{id}/reevaluate", status_code=status.HTTP_202_ACCEPTED)
def reevaluate_conversation(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    member = ProjectService.get_user_member(db, current_user)
    c = ConversationService.get_conversation_with_relations(db, conversation_id=id)

    if not c or (c.project and c.project.organization_id != member.organization_id):
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
    project = ProjectService.get_or_create_user_project(db, current_user)
    active_project_id = payload.projectId or project.id

    member = ProjectService.get_user_member(db, current_user)
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
    member = ProjectService.get_user_member(db, current_user)
    c = ConversationService.get_conversation_with_relations(db, conversation_id=id)

    if not c or (c.project and c.project.organization_id != member.organization_id):
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.delete(c)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
