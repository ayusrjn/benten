import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.schemas.agent import AgentResponse


def _compute_trends_and_problems(convs: list) -> Dict[str, Any]:
    if not convs:
        return {
            "latencyTrend": [],
            "deadAirTrend": [],
            "interruptionsTrend": [],
            "emotionTrend": [],
            "topProblems": []
        }

    latency_trend = [c.latency_ms for c in convs]
    dead_air_trend = [float(c.dead_air_percent) if c.dead_air_percent is not None else 0.0 for c in convs]
    interruptions_trend = [c.interruptions for c in convs]
    emotion_trend = [c.health_score for c in convs]

    top_problems = []
    high_latency = [c.latency_ms for c in convs if c.latency_ms and c.latency_ms > 800]
    if high_latency:
        top_problems.append(f"Turn latency spike ({max(high_latency)}ms detected)")

    high_dead_air = [
        float(c.dead_air_percent)
        for c in convs
        if c.dead_air_percent is not None and float(c.dead_air_percent) > 5.0
    ]
    if high_dead_air:
        top_problems.append(f"Elevated dead air ({max(high_dead_air):.1f}% call duration)")

    high_interr = [c.interruptions for c in convs if c.interruptions and c.interruptions > 3]
    if high_interr:
        top_problems.append(f"Frequent user barge-ins ({max(high_interr)} overlaps)")

    low_health = [c.health_score for c in convs if c.health_score and c.health_score < 70]
    if low_health:
        top_problems.append(f"Quality degraded on recent calls ({min(low_health)}/100)")

    return {
        "latencyTrend": latency_trend,
        "deadAirTrend": dead_air_trend,
        "interruptionsTrend": interruptions_trend,
        "emotionTrend": emotion_trend,
        "topProblems": top_problems
    }


class AgentService:
    @staticmethod
    def get_agent_metrics(db: Session, agent_id: uuid.UUID) -> dict:
        # Normalize to uuid.UUID to prevent SQLite dialect mismatch
        agent_id = uuid.UUID(str(agent_id))
        convs = db.query(Conversation).filter(
            Conversation.agent_id == agent_id,
            Conversation.status == "Completed"
        ).order_by(Conversation.created_at.desc()).limit(7).all()
        convs.reverse()

        conversations_count = db.query(Conversation).filter(Conversation.agent_id == agent_id).count()

        avg_health = db.query(func.avg(Conversation.health_score)).filter(
            Conversation.agent_id == agent_id,
            Conversation.status == "Completed"
        ).scalar()
        health_score = int(round(avg_health)) if avg_health is not None else 100

        metrics = _compute_trends_and_problems(convs)
        metrics["conversationsCount"] = conversations_count
        metrics["healthScore"] = health_score
        return metrics

    @staticmethod
    def build_agent_response(db: Session, a: Agent) -> AgentResponse:
        metrics = AgentService.get_agent_metrics(db, a.id)
        return AgentResponse(
            id=a.id,
            projectId=a.project_id,
            name=a.name,
            provider=a.provider,
            externalId=a.external_id,
            description=a.description,
            lastSyncedAt=a.last_synced_at.isoformat() if a.last_synced_at else None,
            rawMetadata=a.raw_metadata,
            conversationsCount=metrics["conversationsCount"],
            healthScore=metrics["healthScore"],
            latencyTrend=metrics["latencyTrend"],
            deadAirTrend=metrics["deadAirTrend"],
            interruptionsTrend=metrics["interruptionsTrend"],
            emotionTrend=metrics["emotionTrend"],
            topProblems=metrics["topProblems"]
        )

    @staticmethod
    def build_agents_response_batch(db: Session, agents: List[Agent]) -> List[AgentResponse]:
        if not agents:
            return []

        agent_ids = [a.id for a in agents]

        counts_query = db.query(
            Conversation.agent_id,
            func.count(Conversation.id)
        ).filter(
            Conversation.agent_id.in_(agent_ids)
        ).group_by(Conversation.agent_id).all()
        counts_map = {agent_id: cnt for agent_id, cnt in counts_query}

        avg_health_query = db.query(
            Conversation.agent_id,
            func.avg(Conversation.health_score)
        ).filter(
            Conversation.agent_id.in_(agent_ids),
            Conversation.status == "Completed"
        ).group_by(Conversation.agent_id).all()
        avg_health_map = {agent_id: int(round(avg)) if avg is not None else 100 for agent_id, avg in avg_health_query}

        rn_col = func.row_number().over(
            partition_by=Conversation.agent_id,
            order_by=Conversation.created_at.desc()
        ).label("rn")

        subq = db.query(
            Conversation.agent_id.label("agent_id"),
            Conversation.latency_ms.label("latency_ms"),
            Conversation.dead_air_percent.label("dead_air_percent"),
            Conversation.interruptions.label("interruptions"),
            Conversation.health_score.label("health_score"),
            rn_col
        ).filter(
            Conversation.agent_id.in_(agent_ids),
            Conversation.status == "Completed"
        ).subquery()

        recent_convs = db.query(subq).filter(subq.c.rn <= 7).all()

        recent_convs_map = {aid: [] for aid in agent_ids}
        for row in recent_convs:
            recent_convs_map[row.agent_id].append(row)

        responses = []
        for a in agents:
            convs = recent_convs_map.get(a.id, [])
            convs.reverse()

            metrics = _compute_trends_and_problems(convs)

            responses.append(AgentResponse(
                id=a.id,
                projectId=a.project_id,
                name=a.name,
                provider=a.provider,
                externalId=a.external_id,
                description=a.description,
                lastSyncedAt=a.last_synced_at.isoformat() if a.last_synced_at else None,
                rawMetadata=a.raw_metadata,
                conversationsCount=counts_map.get(a.id, 0),
                healthScore=avg_health_map.get(a.id, 100),
                latencyTrend=metrics["latencyTrend"],
                deadAirTrend=metrics["deadAirTrend"],
                interruptionsTrend=metrics["interruptionsTrend"],
                emotionTrend=metrics["emotionTrend"],
                topProblems=metrics["topProblems"]
            ))

        return responses
