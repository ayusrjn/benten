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

    @staticmethod
    def map_conversation_to_response(db: Session, c: Conversation) -> Any:
        from app.schemas.conversation import ConversationResponse, SpeechSegmentResponse
        agent_name = c.agent.name if c.agent else "Unknown Agent"

        # Use pre-loaded speech_segments if available via joinedload (avoids N+1 query)
        segments = c.speech_segments if hasattr(c, "speech_segments") and c.speech_segments is not None else db.query(SpeechSegment).filter(
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
