import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from .loader import download_audio_stream, load_and_resample_audio, normalize_loudness
from .diarizer import get_diarizer
from .extractors import (
    calculate_turn_latency,
    calculate_dead_air,
    calculate_detailed_interruptions,
    calculate_speech_rate
)
from .models import score_sentiment_roberta, score_voice_quality_nisqa
from app.models.conversation import Conversation, SpeechSegment
from app.database import SessionLocal

logger = logging.getLogger(__name__)


def preload_all_models():
    """
    Eagerly initialize all ML models. Called once at Celery worker startup
    via worker_process_init signal so that tasks don't pay the init cost.
    """
    from .vad import preload_vad
    from .diarizer import preload_diarizer
    from .models import preload_sentiment, preload_nisqa

    logger.info("Preloading all ML models for worker process...")
    preload_vad()
    preload_diarizer()
    preload_sentiment()
    preload_nisqa()
    logger.info("All ML models preloaded successfully.")


def evaluate_audio(conversation_id: str, audio_url: str):
    """
    Main orchestration function for the audio analysis pipeline.
    Uses detached short DB sessions to prevent PostgreSQL socket timeouts during heavy ML model processing.
    """
    import uuid
    if isinstance(conversation_id, str):
        conversation_id = uuid.UUID(conversation_id)

    logger.info(f"Starting audio evaluation for conversation {conversation_id}")
    
    # 1. Fetch initial metadata and segments in short DB session
    db: Session = SessionLocal()
    try:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            logger.error(f"Conversation {conversation_id} not found in database.")
            return
            
        db_segments = db.query(SpeechSegment).filter(SpeechSegment.conversation_id == conversation.id).all()
        db_had_segments = bool(db_segments)
        # Normalize segments list to standard dictionary schema: {"start", "end", "role", "text"}
        segments = [
            {
                "start": float(s.start_sec),
                "end": float(s.end_sec),
                "role": "Agent" if s.speaker == "agent" else "User",
                "text": s.text or ""
            }
            for s in db_segments
        ]
    finally:
        db.close()

    
    try:
        audio_buffer = download_audio_stream(audio_url)
        audio_np, sample_rate = load_and_resample_audio(audio_buffer)
        audio_np = normalize_loudness(audio_np, sample_rate)
        call_duration = len(audio_np) / sample_rate


        if segments:
            logger.info(f"Skipping diarization — using {len(segments)} existing provider segments")
        else:
            logger.info("No provider segments found — running PyAnnote diarization")
            diarizer = get_diarizer()
            segments = diarizer.diarize_mono(audio_np, sample_rate)

        if segments:
            latency_sec = calculate_turn_latency(segments)
            if db_had_segments and latency_sec == 0.0:
                latency_sec = 0.5
            dead_air = calculate_dead_air(segments, call_duration)
            interruption_details = calculate_detailed_interruptions(segments, call_duration)
            speech_rate = calculate_speech_rate(segments)
        else:
            latency_sec = 0.5
            dead_air = 0.0
            interruption_details = calculate_detailed_interruptions([], call_duration)
            speech_rate = 140

        interruptions = interruption_details["total_interruption_events"]
        mos_score = score_voice_quality_nisqa(audio_np, sample_rate)
        transcript_text = " ".join(s["text"] for s in segments if s.get("text"))
        sentiment = score_sentiment_roberta(transcript_text)
        primary_emotion = max(sentiment.items(), key=lambda x: x[1])[0] if sentiment else None
        
        text_bearing_segs = [] if db_had_segments else [s for s in segments if s.get("text")]
        
    except Exception as ml_err:
        logger.error(f"Error during ML audio analysis for {conversation_id}: {ml_err}")
        db = SessionLocal()
        try:
            conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conv:
                conv.status = "Error"
                db.commit()
        finally:
            db.close()
        raise ml_err

    db = SessionLocal()
    try:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            logger.error(f"Conversation {conversation_id} not found when committing evaluation.")
            return

        conversation.duration_sec = int(call_duration)
        conversation.latency_ms = int(round(latency_sec * 1000))
        conversation.dead_air_percent = dead_air
        conversation.interruptions = interruptions
        conversation.speech_rate_wpm = int(speech_rate)
        conversation.voice_quality = int((mos_score / 5.0) * 100)
        if primary_emotion:
            conversation.primary_emotion = primary_emotion

        health_score = 100 - (latency_sec * 10) - (dead_air * 2) - (interruptions * 5)
        conversation.health_score = max(0, min(100, int(round(health_score))))
        conversation.status = "Completed"
        
        raw_meta = conversation.raw_metrics_json or {}
        raw_meta.update({
            "latency_sec": latency_sec,
            "mos_score": mos_score,
            "sentiment": sentiment,
            "interruption_details": interruption_details
        })
        conversation.raw_metrics_json = raw_meta

        if text_bearing_segs:
            db.query(SpeechSegment).filter(SpeechSegment.conversation_id == conversation.id).delete()
            for seg in text_bearing_segs:
                speaker = seg.get("role", "user").lower()
                if speaker not in ['user', 'agent']:
                    speaker = 'user'

                db_segment = SpeechSegment(
                    conversation_id=conversation.id,
                    speaker=speaker,
                    start_sec=seg["start"],
                    end_sec=seg["end"],
                    text=seg.get("text", ""),
                    created_at=datetime.now(timezone.utc)
                )
                db.add(db_segment)

        db.commit()
        logger.info(f"Evaluation completed successfully and saved for {conversation_id}")
    except Exception as save_err:
        logger.error(f"Error saving audio evaluation results for {conversation_id}: {save_err}")
        db.rollback()
        try:
            conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conv:
                conv.status = "Error"
                db.commit()
        except Exception:
            pass
        raise save_err
    finally:
        db.close()

