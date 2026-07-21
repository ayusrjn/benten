import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.security import get_current_active_user
from app.models.user import User
from app.models.project import Project
from app.models.agent import Agent
from app.models.integration import Integration
from app.models.organization import Member
from app.services.project_service import ProjectService, PROVIDER_NAME_TO_KEY
from app.services.integration_service import IntegrationService
from app.services.agent_service import AgentService
from app.schemas import (
    AgentResponse,
    AgentCreate,
    AgentUpdate,
    GlobalSyncAgentsResponse,
)

router = APIRouter(prefix="/agents", tags=["Agents"])

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
    project = ProjectService.get_or_create_user_project(db, current_user)
    active_project_id = projectId or project.id
    
    member = ProjectService.get_user_member(db, current_user)
    proj = db.query(Project).filter(Project.id == active_project_id, Project.organization_id == member.organization_id).first()
    if not proj:
        raise HTTPException(status_code=403, detail="Access to specified project denied")
        
    query = db.query(Agent).filter(Agent.project_id == active_project_id)
    
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
    
    if _start is not None and _end is not None:
        query = query.offset(_start).limit(_end - _start)
        
    agents = query.all()
    return AgentService.build_agents_response_batch(db, agents)


@router.post("/sync", response_model=GlobalSyncAgentsResponse)
def sync_all_agents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = ProjectService.get_or_create_user_project(db, current_user)
    integrations = db.query(Integration).filter(
        Integration.project_id == project.id,
        Integration.connected == True
    ).all()

    total_synced = 0
    synced_providers = []

    for integ in integrations:
        provider_key = PROVIDER_NAME_TO_KEY.get(integ.name, integ.name.lower())
        raw_key = IntegrationService.get_decrypted_key(integ)
        if raw_key:
            agents = IntegrationService.sync_agents(db, project.id, provider_key, raw_key)
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
    member = ProjectService.get_user_member(db, current_user)
    
    a = db.query(Agent).join(Project).filter(
        Agent.id == id,
        Project.organization_id == member.organization_id
    ).first()
    
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    return AgentService.build_agent_response(db, a)


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    payload: AgentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    default_project = ProjectService.get_or_create_user_project(db, current_user)
    active_project_id = payload.projectId or default_project.id
    
    member = ProjectService.get_user_member(db, current_user)
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
    
    return AgentService.build_agent_response(db, new_agent)


@router.put("/{id}", response_model=AgentResponse)
@router.patch("/{id}", response_model=AgentResponse)
def update_agent(
    id: uuid.UUID,
    payload: AgentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    member = ProjectService.get_user_member(db, current_user)
    
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
    
    return AgentService.build_agent_response(db, a)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    member = ProjectService.get_user_member(db, current_user)
    
    a = db.query(Agent).join(Project).filter(
        Agent.id == id,
        Project.organization_id == member.organization_id
    ).first()
    
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    db.delete(a)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
