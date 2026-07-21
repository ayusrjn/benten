from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.security import get_current_active_user
from app.models.user import User
from app.models.project import Project
from app.models.organization import Organization, Member
from app.models.integration import Integration
from app.services.project_service import ProjectService

router = APIRouter(prefix="/organization", tags=["Organization"])


from app.schemas import OrgStatsResponse, MemberResponse, MemberInvite

@router.get("", response_model=OrgStatsResponse)
def get_organization_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = ProjectService.get_or_create_user_project(db, current_user)
    
    member = db.query(Member).filter(Member.email == current_user.email).first()
    if not member:
        raise HTTPException(status_code=404, detail="User organization membership not found")
        
    org = db.query(Organization).filter(Organization.id == member.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    # Count members
    members_count = db.query(Member).filter(Member.organization_id == org.id).count()
    
    # Count projects
    projects_count = db.query(Project).filter(Project.organization_id == org.id).count()
    
    # Count connected integrations as API Keys Count
    api_keys_count = db.query(Integration).join(Project).filter(
        Project.organization_id == org.id,
        Integration.connected == True
    ).count()
    
    # Mock some realistic storage details
    return OrgStatsResponse(
        id=org.id,
        name=org.name,
        membersCount=members_count,
        projectsCount=projects_count,
        apiKeysCount=api_keys_count,
        storageUsedGb=42, # Realistic hardcoded dev values
        storageLimitGb=100
    )

@router.get("/members", response_model=List[MemberResponse])
def list_organization_members(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = ProjectService.get_or_create_user_project(db, current_user)
    
    member = db.query(Member).filter(Member.email == current_user.email).first()
    if not member:
        raise HTTPException(status_code=404, detail="User organization membership not found")
        
    members = db.query(Member).filter(Member.organization_id == member.organization_id).all()
    
    response_list = []
    for m in members:
        name = m.email.split("@")[0].capitalize()
        # Find user if exists to get full_name
        u = db.query(User).filter(User.email == m.email).first()
        if u and u.full_name:
            name = u.full_name
            
        avatar_url = m.avatar_url or f"https://i.pravatar.cc/150?u={m.id}"
        
        response_list.append(MemberResponse(
            id=m.id,
            name=name,
            email=m.email,
            role=m.role,
            avatar=avatar_url
        ))
        
    response.headers["x-total-count"] = str(len(response_list))
    return response_list

@router.post("/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def invite_member(
    payload: MemberInvite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = ProjectService.get_or_create_user_project(db, current_user)
    
    member = db.query(Member).filter(Member.email == current_user.email).first()
    if not member:
        raise HTTPException(status_code=404, detail="User organization membership not found")
        
    # Check if already a member
    existing = db.query(Member).filter(
        Member.organization_id == member.organization_id,
        Member.email == payload.email
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User is already a member of this organization")
        
    new_member = Member(
        organization_id=member.organization_id,
        email=payload.email,
        role=payload.role or "Viewer",
        avatar_url=f"https://i.pravatar.cc/150?img={hash(payload.email) % 70}"
    )
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    
    name = payload.email.split("@")[0].capitalize()
    return MemberResponse(
        id=new_member.id,
        name=name,
        email=new_member.email,
        role=new_member.role,
        avatar=new_member.avatar_url
    )
