from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.security import get_current_active_user
from app.models.user import User
from app.models.project import Project
from app.services.project_service import ProjectService
from app.services.conversation_service import ConversationService
from app.schemas import (
    SpeechSegmentResponse,
    ConversationResponse,
    ConversationIngestRequest,
)

router = APIRouter(prefix="/conversations", tags=["Conversations"])

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
    return [ConversationService.map_conversation_to_response(db, c) for c in conversations]


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

    return ConversationService.map_conversation_to_response(db, c)


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
