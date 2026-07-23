import json
import logging
import redis
from app.config import settings
from app.database import SessionLocal
from app.models.conversation import Conversation, SpeechSegment

logger = logging.getLogger(__name__)


def process_audio_evaluation(conversation_id: str, audio_url: str) -> bool:
    """
    Evaluates call audio using the ML pipeline, falling back to a transcript segment heuristic
    if the pipeline is unavailable, and announces completion via Redis.
    """
    db = SessionLocal()
    try:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            logger.error(f"Conversation {conversation_id} not found.")
            return False
        project_id = str(conversation.project_id)
    finally:
        db.close()

    pipeline_success = False
    try:
        from app.pipeline.scoring import evaluate_audio as run_real_evaluation
        run_real_evaluation(conversation_id, audio_url)
        pipeline_success = True
        logger.info("ML evaluation pipeline completed successfully.")
    except Exception as pipeline_err:
        logger.warning(f"ML evaluation failed ({pipeline_err}). Using segment validation fallback.")

    if not pipeline_success:
        db = SessionLocal()
        try:
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            segments = db.query(SpeechSegment).filter(SpeechSegment.conversation_id == conversation_id).all()
            
            if segments:
                sorted_segs = sorted(segments, key=lambda s: float(s.start_sec))
                latencies = []
                interruptions = 0
                total_speech = 0.0
                total_words = 0

                for i, seg in enumerate(sorted_segs):
                    start = float(seg.start_sec)
                    end = float(seg.end_sec)
                    total_speech += max(0.0, end - start)
                    
                    if seg.text:
                        total_words += len(seg.text.split())

                    if i > 0:
                        prev_seg = sorted_segs[i - 1]
                        prev_end = float(prev_seg.end_sec)
                        if start < prev_end and prev_seg.speaker != seg.speaker:
                            interruptions += 1
                        if prev_seg.speaker == "user" and seg.speaker == "agent":
                            pause = start - prev_end
                            if pause >= 0:
                                latencies.append(pause)

                avg_latency = (sum(latencies) / len(latencies)) if latencies else 0.5
                duration = float(conversation.duration_sec or (sorted_segs[-1].end_sec if sorted_segs else 1.0))
                
                dead_air_sec = max(0.0, duration - total_speech)
                dead_air_pct = round((dead_air_sec / duration) * 100.0, 2) if duration > 0.0 else 0.0
                wpm = int(round((total_words / (total_speech / 60.0)))) if total_speech > 0.0 else 140
                
                calculated_score = max(0, min(100, int(round(100 - (avg_latency * 10) - (dead_air_pct * 2) - (interruptions * 5)))))

                conversation.status = "Completed"
                conversation.health_score = calculated_score
                conversation.latency_ms = int(round(avg_latency * 1000))
                conversation.dead_air_percent = dead_air_pct
                conversation.interruptions = interruptions
                conversation.speech_rate_wpm = wpm
                conversation.voice_quality = min(100, max(60, calculated_score))
                conversation.primary_emotion = "neutral"
            else:
                conversation.status = "Completed"
                conversation.health_score = None

            db.commit()
            logger.info(f"Segment evaluation complete: score={conversation.health_score} for {conversation_id}")
        finally:
            db.close()

    try:
        r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
        event = {
            "type": "conversation_completed",
            "conversation_id": conversation_id,
            "project_id": project_id
        }
        r.publish("benten-updates", json.dumps(event))
    except Exception as redis_err:
        logger.error(f"Redis completion signal failed: {redis_err}")

    return True
