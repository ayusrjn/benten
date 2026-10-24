from typing import Optional
from datetime import datetime, timedelta, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.security import get_current_active_user
from app.models.user import User
from app.models.project import Project
from app.models.conversation import Conversation
from app.models.alert import Alert
from app.models.organization import Member
from app.services.project_service import ProjectService
from app.schemas import DashboardAlertResponse, DashboardMetricsResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/metrics", response_model=DashboardMetricsResponse)
def get_dashboard_metrics(
    projectId: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = ProjectService.get_or_create_user_project(db, current_user)
    active_project_id = projectId or project.id
    
    member = db.query(Member).filter(Member.email == current_user.email).first()
    proj = db.query(Project).filter(Project.id == active_project_id, Project.organization_id == member.organization_id).first()
    if not proj:
        raise HTTPException(status_code=403, detail="Access denied to specified project")
        
    # Get completed conversations
    convs_query = db.query(Conversation).filter(
        Conversation.project_id == active_project_id,
        Conversation.status == "Completed"
    )
    
    total_convs = convs_query.count()
    
    # Calculate averages
    avg_stats = db.query(
        func.avg(Conversation.latency_ms),
        func.avg(Conversation.dead_air_percent),
        func.sum(Conversation.interruptions),
        func.avg(Conversation.voice_quality),
        func.avg(Conversation.duration_sec)
    ).filter(
        Conversation.project_id == active_project_id,
        Conversation.status == "Completed"
    ).first()
    
    latency_avg = int(round(avg_stats[0])) if avg_stats and avg_stats[0] is not None else None
    dead_air_avg = float(round(avg_stats[1], 2)) if avg_stats and avg_stats[1] is not None else None
    interruptions_count = int(avg_stats[2]) if avg_stats and avg_stats[2] is not None else 0
    voice_quality_avg = int(round(avg_stats[3])) if avg_stats and avg_stats[3] is not None else None
    avg_duration_sec = int(round(avg_stats[4])) if avg_stats and avg_stats[4] is not None else None
    
    # Latency trend over last 10 conversations
    last_10 = db.query(Conversation.latency_ms).filter(
        Conversation.project_id == active_project_id,
        Conversation.status == "Completed"
    ).order_by(Conversation.created_at.desc()).limit(10).all()
    
    latency_trend = [item[0] for item in last_10]
    latency_trend.reverse()
    
    # Seven UTC calendar days of actual ingested calls, including all statuses.
    today = datetime.now(timezone.utc).date()
    first_day = today - timedelta(days=6)
    window_start = datetime.combine(first_day, datetime.min.time(), tzinfo=timezone.utc)
    window_end = window_start + timedelta(days=7)
    created_at = Conversation.created_at
    if db.get_bind().dialect.name == "postgresql":
        created_at = func.timezone("UTC", created_at)
    day = func.date(created_at)
    daily_counts = db.query(day, func.count(Conversation.id)).filter(
        Conversation.project_id == active_project_id,
        Conversation.created_at >= window_start,
        Conversation.created_at < window_end,
    ).group_by(day).all()
    counts = {str(date): count for date, count in daily_counts}
    volume_dates = [(first_day + timedelta(days=i)).isoformat() for i in range(7)]
    volume_trend = [counts.get(date, 0) for date in volume_dates] if counts else []
    if not counts:
        volume_dates = []

    # Active alerts
    active_alerts_db = db.query(Alert).filter(
        Alert.project_id == active_project_id,
        Alert.status == "Triggered"
    ).order_by(Alert.triggered_at.desc()).limit(5).all()
    
    active_alerts = []
    for a in active_alerts_db:
        rule_metric = a.alert_rule.metric if a.alert_rule else "High Latency"
        
        agent_name = "Agent"
        if a.conversation and a.conversation.agent:
            agent_name = a.conversation.agent.name
            
        desc = f"Response latency spiked to {a.conversation.latency_ms}ms on {agent_name}" if a.conversation else f"{rule_metric} threshold triggered"
        alert_type = "error" if "Quality" in rule_metric or "Critical" in a.status else "warning"
        
        active_alerts.append(DashboardAlertResponse(
            id=a.id,
            title=f"{rule_metric} on {agent_name}",
            desc=desc,
            type=alert_type
        ))
        
    return DashboardMetricsResponse(
        conversationsCount=total_convs,
        latencyAvg=latency_avg,
        deadAirAvg=dead_air_avg,
        interruptionsCount=interruptions_count,
        voiceQualityAvg=voice_quality_avg,
        avgDurationSec=avg_duration_sec,
        latencyTrend=latency_trend,
        volumeTrend=volume_trend,
        volumeDates=volume_dates,
        activeAlerts=active_alerts
    )
