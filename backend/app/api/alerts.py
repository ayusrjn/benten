from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.security import get_current_active_user
from app.models.user import User
from app.models.project import Project
from app.models.alert import Alert, AlertRule
from app.models.organization import Member
from app.services.project_service import ProjectService
from app.utils.datetime_utils import get_time_text
from app.schemas import AlertRuleResponse, AlertRuleCreate, AlertRuleUpdate, AlertResponse

# We export two routers from this file
alerts_router = APIRouter(prefix="/alerts", tags=["Alerts"])
rules_router = APIRouter(prefix="/alert_rules", tags=["Alert Rules"])

# ==========================================
# ALERTS ROUTER (Incident Log)
# ==========================================

@alerts_router.get("", response_model=List[AlertResponse])
def list_alerts(
    response: Response,
    projectId: Optional[uuid.UUID] = None,
    _start: Optional[int] = None,
    _end: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = ProjectService.get_or_create_user_project(db, current_user)
    active_project_id = projectId or project.id
    
    member = db.query(Member).filter(Member.email == current_user.email).first()
    proj = db.query(Project).filter(Project.id == active_project_id, Project.organization_id == member.organization_id).first()
    if not proj:
        raise HTTPException(status_code=403, detail="Access denied to specified project")
        
    query = db.query(Alert).filter(Alert.project_id == active_project_id).order_by(Alert.triggered_at.desc())
    
    total = query.count()
    response.headers["x-total-count"] = str(total)
    
    if _start is not None and _end is not None:
        query = query.offset(_start).limit(_end - _start)
        
    alerts = query.all()
    
    result = []
    for a in alerts:
        rule_metric = a.alert_rule.metric if a.alert_rule else "Evaluation Alert"
        rule_threshold = a.alert_rule.threshold if a.alert_rule else ""
        rule_duration = a.alert_rule.duration if a.alert_rule else ""
        
        agent_name = "Unknown Agent"
        if a.conversation and a.conversation.agent:
            agent_name = a.conversation.agent.name
            
        metric_desc = f"{rule_metric} {rule_threshold}"
        if rule_duration:
            metric_desc += f" for {rule_duration}"
            
        result.append(AlertResponse(
            id=a.id,
            name=rule_metric,
            status=a.status,
            agentName=agent_name,
            timeText=get_time_text(a.triggered_at),
            metric=metric_desc
        ))
        
    return result

# ==========================================
# ALERT RULES ROUTER (CRUD)
# ==========================================

@rules_router.get("", response_model=List[AlertRuleResponse])
def list_alert_rules(
    response: Response,
    projectId: Optional[uuid.UUID] = None,
    _start: Optional[int] = None,
    _end: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = ProjectService.get_or_create_user_project(db, current_user)
    active_project_id = projectId or project.id
    
    member = db.query(Member).filter(Member.email == current_user.email).first()
    proj = db.query(Project).filter(Project.id == active_project_id, Project.organization_id == member.organization_id).first()
    if not proj:
        raise HTTPException(status_code=403, detail="Access denied to specified project")
        
    query = db.query(AlertRule).filter(AlertRule.project_id == active_project_id).order_by(AlertRule.created_at.desc())
    
    total = query.count()
    response.headers["x-total-count"] = str(total)
    
    if _start is not None and _end is not None:
        query = query.offset(_start).limit(_end - _start)
        
    rules = query.all()
    return rules

@rules_router.post("", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
def create_alert_rule(
    payload: AlertRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = ProjectService.get_or_create_user_project(db, current_user)
    active_project_id = payload.projectId or project.id
    
    member = db.query(Member).filter(Member.email == current_user.email).first()
    proj = db.query(Project).filter(Project.id == active_project_id, Project.organization_id == member.organization_id).first()
    if not proj:
        raise HTTPException(status_code=403, detail="Access denied to specified project")
        
    new_rule = AlertRule(
        project_id=active_project_id,
        metric=payload.metric,
        threshold=payload.threshold,
        duration=payload.duration,
        action=payload.action
    )
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)
    return new_rule

@rules_router.put("/{id}", response_model=AlertRuleResponse)
@rules_router.patch("/{id}", response_model=AlertRuleResponse)
def update_alert_rule(
    id: uuid.UUID,
    payload: AlertRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    member = db.query(Member).filter(Member.email == current_user.email).first()
    
    rule = db.query(AlertRule).join(Project).filter(
        AlertRule.id == id,
        Project.organization_id == member.organization_id
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
        
    if payload.metric is not None:
        rule.metric = payload.metric
    if payload.threshold is not None:
        rule.threshold = payload.threshold
    if payload.duration is not None:
        rule.duration = payload.duration
    if payload.action is not None:
        rule.action = payload.action
        
    db.commit()
    db.refresh(rule)
    return rule

@rules_router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert_rule(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    member = db.query(Member).filter(Member.email == current_user.email).first()
    
    rule = db.query(AlertRule).join(Project).filter(
        AlertRule.id == id,
        Project.organization_id == member.organization_id
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
        
    db.delete(rule)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
