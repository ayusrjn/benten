from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.security import get_current_active_user
from app.models.user import User
from app.models.project import Project
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.integration import Integration
from app.models.organization import Member
from app.api.integrations import get_or_create_user_project, sync_agents_for_integration, PROVIDER_NAME_TO_KEY

router = APIRouter(prefix="/agents", tags=["Agents"])

class AgentResponse(BaseModel):
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

    class Config:
        from_attributes = True

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

def get_agent_metrics(db: Session, agent: Agent) -> dict:
    # Query last 7 completed conversations to build trends
    convs = db.query(Conversation).filter(
        Conversation.agent_id == agent.id,
        Conversation.status == "Completed"
    ).order_by(Conversation.created_at.desc()).limit(7).all()
    
    # Reverse to show chronological order (left to right)
    convs.reverse()
    
    conversations_count = db.query(Conversation).filter(Conversation.agent_id == agent.id).count()
    
    avg_health = db.query(func.avg(Conversation.health_score)).filter(
        Conversation.agent_id == agent.id,
        Conversation.status == "Completed"
    ).scalar()
    health_score = int(round(avg_health)) if avg_health is not None else 100
    
    # Extract real trends directly from completed conversations
    latency_trend = [c.latency_ms for c in convs]
    dead_air_trend = [float(c.dead_air_percent) for c in convs]
    interruptions_trend = [c.interruptions for c in convs]
    emotion_trend = [c.health_score for c in convs]
    
    # Calculate real top problems / incident flags from evaluated call records
    top_problems = []
    if convs:
        high_latency_calls = [c for c in convs if c.latency_ms and c.latency_ms > 800]
        if high_latency_calls:
            max_lat = max(c.latency_ms for c in high_latency_calls)
            top_problems.append(f"Turn latency spike ({max_lat}ms detected)")
            
        high_dead_air_calls = [c for c in convs if c.dead_air_percent and float(c.dead_air_percent) > 5.0]
        if high_dead_air_calls:
            max_da = max(float(c.dead_air_percent) for c in high_dead_air_calls)
            top_problems.append(f"Elevated dead air ({max_da:.1f}% call duration)")
            
        high_interr_calls = [c for c in convs if c.interruptions and c.interruptions > 3]
        if high_interr_calls:
            max_int = max(c.interruptions for c in high_interr_calls)
            top_problems.append(f"Frequent user barge-ins ({max_int} overlaps)")
            
        low_health_calls = [c for c in convs if c.health_score and c.health_score < 70]
        if low_health_calls:
            min_hs = min(c.health_score for c in low_health_calls)
            top_problems.append(f"Quality degraded on recent calls ({min_hs}/100)")
            
    return {
        "conversationsCount": conversations_count,
        "healthScore": health_score,
        "latencyTrend": latency_trend,
        "deadAirTrend": dead_air_trend,
        "interruptionsTrend": interruptions_trend,
        "emotionTrend": emotion_trend,
        "topProblems": top_problems
    }

def build_agent_response(db: Session, a: Agent) -> AgentResponse:
    metrics = get_agent_metrics(db, a)
    last_synced_str = a.last_synced_at.isoformat() if a.last_synced_at else None
    return AgentResponse(
        id=a.id,
        projectId=a.project_id,
        name=a.name,
        provider=a.provider,
        externalId=a.external_id,
        description=a.description,
        lastSyncedAt=last_synced_str,
        rawMetadata=a.raw_metadata,
        conversationsCount=metrics["conversationsCount"],
        healthScore=metrics["healthScore"],
        latencyTrend=metrics["latencyTrend"],
        deadAirTrend=metrics["deadAirTrend"],
        interruptionsTrend=metrics["interruptionsTrend"],
        emotionTrend=metrics["emotionTrend"],
        topProblems=metrics["topProblems"]
    )

@router.get("", response_model=List[AgentResponse])
def list_agents(
    response: Response,
    projectId: Optional[uuid.UUID] = None,
    _start: Optional[int] = None,
    _end: Optional[int] = None,
    _sort: Optional[str] = None,
    _order: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = get_or_create_user_project(db, current_user)
    active_project_id = projectId or project.id
    
    # Verify project belongs to user's org
    member = db.query(Member).filter(Member.email == current_user.email).first()
    proj = db.query(Project).filter(Project.id == active_project_id, Project.organization_id == member.organization_id).first()
    if not proj:
        raise HTTPException(status_code=403, detail="Access to specified project denied")
        
    query = db.query(Agent).filter(Agent.project_id == active_project_id)
    
    # Sort
    if _sort:
        col = getattr(Agent, _sort, None)
        if col is not None:
            if _order and _order.lower() == "desc":
                query = query.order_by(col.desc())
            else:
                query = query.order_by(col.asc())
    else:
        query = query.order_by(Agent.created_at.desc())
        
    total = query.count()
    response.headers["x-total-count"] = str(total)
    
    # Paginate
    if _start is not None and _end is not None:
        query = query.offset(_start).limit(_end - _start)
        
    agents = query.all()
    return [build_agent_response(db, a) for a in agents]

class GlobalSyncAgentsResponse(BaseModel):
    success: bool
    totalSynced: int
    message: str

@router.post("/sync", response_model=GlobalSyncAgentsResponse)
def sync_all_agents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = get_or_create_user_project(db, current_user)
    integrations = db.query(Integration).filter(
        Integration.project_id == project.id,
        Integration.connected == True
    ).all()

    total_synced = 0
    synced_providers = []

    for integ in integrations:
        provider_key = PROVIDER_NAME_TO_KEY.get(integ.name, integ.name.lower())
        if integ.api_key:
            agents = sync_agents_for_integration(db, project.id, provider_key, integ.api_key)
            total_synced += len(agents)
            synced_providers.append(integ.name)

    if not integrations:
        return GlobalSyncAgentsResponse(
            success=False,
            totalSynced=0,
            message="No connected integrations found. Connect an integration under Settings/Integrations first."
        )

    return GlobalSyncAgentsResponse(
        success=True,
        totalSynced=total_synced,
        message=f"Synced {total_synced} agents across providers: {', '.join(synced_providers)}"
    )

@router.get("/{id}", response_model=AgentResponse)
def get_agent(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    member = db.query(Member).filter(Member.email == current_user.email).first()
    
    a = db.query(Agent).join(Project).filter(
        Agent.id == id,
        Project.organization_id == member.organization_id
    ).first()
    
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    return build_agent_response(db, a)

@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    payload: AgentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    default_project = get_or_create_user_project(db, current_user)
    active_project_id = payload.projectId or default_project.id
    
    member = db.query(Member).filter(Member.email == current_user.email).first()
    proj = db.query(Project).filter(Project.id == active_project_id, Project.organization_id == member.organization_id).first()
    if not proj:
        raise HTTPException(status_code=403, detail="Access denied to specified project")
        
    new_agent = Agent(
        project_id=active_project_id,
        name=payload.name,
        provider=payload.provider,
        external_id=payload.externalId,
        description=payload.description
    )
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)
    
    return build_agent_response(db, new_agent)

@router.put("/{id}", response_model=AgentResponse)
@router.patch("/{id}", response_model=AgentResponse)
def update_agent(
    id: uuid.UUID,
    payload: AgentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    member = db.query(Member).filter(Member.email == current_user.email).first()
    
    a = db.query(Agent).join(Project).filter(
        Agent.id == id,
        Project.organization_id == member.organization_id
    ).first()
    
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    if payload.name is not None:
        a.name = payload.name
    if payload.provider is not None:
        a.provider = payload.provider
    if payload.description is not None:
        a.description = payload.description
        
    db.commit()
    db.refresh(a)
    
    return build_agent_response(db, a)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    member = db.query(Member).filter(Member.email == current_user.email).first()
    
    a = db.query(Agent).join(Project).filter(
        Agent.id == id,
        Project.organization_id == member.organization_id
    ).first()
    
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    db.delete(a)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

