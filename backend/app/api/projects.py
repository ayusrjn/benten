from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.security import get_current_active_user
from app.models.user import User
from app.models.project import Project
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.organization import Member
from app.services.project_service import ProjectService
from app.schemas import ProjectResponse, ProjectCreate, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.get("", response_model=List[ProjectResponse])
def list_projects(
    response: Response,
    _start: Optional[int] = None,
    _end: Optional[int] = None,
    _sort: Optional[str] = None,
    _order: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Ensure default user project / org is created
    ProjectService.get_or_create_user_project(db, current_user)

    
    member = db.query(Member).filter(Member.email == current_user.email).first()
    if not member:
        raise HTTPException(status_code=404, detail="User organization membership not found")
        
    query = db.query(Project).filter(Project.organization_id == member.organization_id)
    
    # Sort
    if _sort:
        col = getattr(Project, _sort, None)
        if col is not None:
            if _order and _order.lower() == "desc":
                query = query.order_by(col.desc())
            else:
                query = query.order_by(col.asc())
    else:
        query = query.order_by(Project.created_at.desc())
        
    total = query.count()
    response.headers["x-total-count"] = str(total)
    
    # Paginate
    if _start is not None and _end is not None:
        query = query.offset(_start).limit(_end - _start)
        
    projects = query.all()
    
    result = []
    for p in projects:
        agents_count = db.query(Agent).filter(Agent.project_id == p.id).count()
        convs_count = db.query(Conversation).filter(Conversation.project_id == p.id).count()
        
        # Calculate average health score
        avg_health = db.query(func.avg(Conversation.health_score)).filter(
            Conversation.project_id == p.id,
            Conversation.status == "Completed"
        ).scalar()
        
        # Default average health to 100 if there are no conversations
        avg_health_val = int(round(avg_health)) if avg_health is not None else 100
        
        result.append(ProjectResponse(
            id=p.id,
            name=p.name,
            agentsCount=agents_count,
            conversationsCount=convs_count,
            avgHealth=avg_health_val
        ))
        
    return result

@router.get("/{id}", response_model=ProjectResponse)
def get_project(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    member = db.query(Member).filter(Member.email == current_user.email).first()
    if not member:
        raise HTTPException(status_code=404, detail="User organization membership not found")
        
    p = db.query(Project).filter(
        Project.id == id,
        Project.organization_id == member.organization_id
    ).first()
    
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
        
    agents_count = db.query(Agent).filter(Agent.project_id == p.id).count()
    convs_count = db.query(Conversation).filter(Conversation.project_id == p.id).count()
    
    avg_health = db.query(func.avg(Conversation.health_score)).filter(
        Conversation.project_id == p.id,
        Conversation.status == "Completed"
    ).scalar()
    avg_health_val = int(round(avg_health)) if avg_health is not None else 100
    
    return ProjectResponse(
        id=p.id,
        name=p.name,
        agentsCount=agents_count,
        conversationsCount=convs_count,
        avgHealth=avg_health_val
    )

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    member = db.query(Member).filter(Member.email == current_user.email).first()
    if not member:
        raise HTTPException(status_code=404, detail="User organization membership not found")
        
    new_project = Project(
        organization_id=member.organization_id,
        name=payload.name
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    
    return ProjectResponse(
        id=new_project.id,
        name=new_project.name,
        agentsCount=0,
        conversationsCount=0,
        avgHealth=100
    )

@router.put("/{id}", response_model=ProjectResponse)
@router.patch("/{id}", response_model=ProjectResponse)
def update_project(
    id: uuid.UUID,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    member = db.query(Member).filter(Member.email == current_user.email).first()
    if not member:
        raise HTTPException(status_code=404, detail="User organization membership not found")
        
    p = db.query(Project).filter(
        Project.id == id,
        Project.organization_id == member.organization_id
    ).first()
    
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
        
    p.name = payload.name
    db.commit()
    db.refresh(p)
    
    agents_count = db.query(Agent).filter(Agent.project_id == p.id).count()
    convs_count = db.query(Conversation).filter(Conversation.project_id == p.id).count()
    
    avg_health = db.query(func.avg(Conversation.health_score)).filter(
        Conversation.project_id == p.id,
        Conversation.status == "Completed"
    ).scalar()
    avg_health_val = int(round(avg_health)) if avg_health is not None else 100
    
    return ProjectResponse(
        id=p.id,
        name=p.name,
        agentsCount=agents_count,
        conversationsCount=convs_count,
        avgHealth=avg_health_val
    )

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    member = db.query(Member).filter(Member.email == current_user.email).first()
    if not member:
        raise HTTPException(status_code=404, detail="User organization membership not found")
        
    p = db.query(Project).filter(
        Project.id == id,
        Project.organization_id == member.organization_id
    ).first()
    
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
        
    db.delete(p)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
