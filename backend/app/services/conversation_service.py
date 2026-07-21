import uuid
import logging
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_

from app.models.conversation import Conversation, SpeechSegment
from app.models.agent import Agent

logger = logging.getLogger(__name__)

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


class ConversationService:
    @staticmethod
    def get_conversation_with_relations(db: Session, conversation_id: uuid.UUID, project_id: Optional[uuid.UUID] = None) -> Conversation | None:
        """
        Retrieves a single conversation with eager-loaded speech_segments and agent.
        """
        query = db.query(Conversation).options(
            joinedload(Conversation.speech_segments),
            joinedload(Conversation.agent)
        ).filter(Conversation.id == conversation_id)

        if project_id:
            query = query.filter(Conversation.project_id == project_id)

        return query.first()

    @staticmethod
    def list_conversations(
        db: Session,
        project_id: uuid.UUID,
        agent_id: Optional[uuid.UUID] = None,
        provider: Optional[str] = None,
        status: Optional[str] = None,
        grade: Optional[str] = None,
        min_score: Optional[int] = None,
        max_score: Optional[int] = None,
        min_duration: Optional[int] = None,
        max_duration: Optional[int] = None,
        max_latency: Optional[int] = None,
        start: Optional[int] = None,
        end: Optional[int] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        q: Optional[str] = None
    ) -> Tuple[List[Conversation], int]:
        """
        Lists project conversations using eager loading (`joinedload`) to prevent N+1 query overhead.
        Returns (conversations_list, total_count).
        """
        query = db.query(Conversation).options(
            joinedload(Conversation.speech_segments),
            joinedload(Conversation.agent)
        ).filter(Conversation.project_id == project_id)

        # Filter by Agent
        if agent_id:
            query = query.filter(Conversation.agent_id == agent_id)

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

        if min_score is not None:
            query = query.filter(Conversation.health_score >= min_score)

        if max_score is not None:
            query = query.filter(Conversation.health_score <= max_score)

        # Filter by Duration
        if min_duration is not None:
            query = query.filter(Conversation.duration_sec >= min_duration)

        if max_duration is not None:
            query = query.filter(Conversation.duration_sec <= max_duration)

        # Filter by Max Latency
        if max_latency is not None:
            query = query.filter(Conversation.latency_ms <= max_latency)

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

        # Total count before pagination
        total = query.count()

        # Sorting
        if sort:
            col = None
            if sort in ("score", "health_score"):
                col = Conversation.health_score
            elif sort in ("duration", "duration_sec"):
                col = Conversation.duration_sec
            elif sort in ("date", "created_at"):
                col = Conversation.created_at
            else:
                col = getattr(Conversation, sort, None)

            if col is not None:
                if order and order.lower() == "desc":
                    query = query.order_by(col.desc())
                else:
                    query = query.order_by(col.asc())
        else:
            query = query.order_by(Conversation.created_at.desc())

        # Pagination
        if start is not None and end is not None:
            query = query.offset(start).limit(end - start)

        conversations = query.all()
        return conversations, total
