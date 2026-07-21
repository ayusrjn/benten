import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json

from .loader import download_audio_stream, load_and_resample_audio, normalize_loudness
from .vad import get_vad
from .diarizer import get_diarizer
from .extractors import (
    calculate_turn_latency,
    calculate_dead_air,
    calculate_interruptions,
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
    from .models import preload_sentiment

    logger.info("Preloading all ML models for worker process...")
    preload_vad()
    preload_diarizer()
    preload_sentiment()
    logger.info("All ML models preloaded successfully.")


def evaluate_audio(conversation_id: str, audio_url: str):
    """
    Main orchestration function for the audio analysis pipeline.
    Uses detached short DB sessions to prevent PostgreSQL socket timeouts during heavy ML model processing.
    """
    logger.info(f"Starting audio evaluation for conversation {conversation_id}")
    
    # 1. Fetch initial metadata in short DB session
    db: Session = SessionLocal()
    try:
        conversation = db.query(Conversation).filter(Conversation.id == str(conversation_id)).first()
        if not conversation:
            logger.error(f"Conversation {conversation_id} not found in database.")
            return
            
        db_segments = db.query(SpeechSegment).filter(SpeechSegment.conversation_id == conversation.id).all()
        # Copy segments into pure python dicts so session can be safely closed
        db_seg_data = [
            {
                "start_sec": float(s.start_sec),
                "end_sec": float(s.end_sec),
                "speaker": s.speaker,
                "text": s.text or ""
            }
            for s in db_segments
        ]
    finally:
        db.close()

    # 2. Heavy Audio Processing & ML Models (NO open database connection)
    try:
        audio_buffer = download_audio_stream(audio_url)
        audio_np, sample_rate = load_and_resample_audio(audio_buffer)
        audio_np = normalize_loudness(audio_np, sample_rate)
        call_duration = len(audio_np) / sample_rate

        # --- KEY OPTIMIZATION: Skip diarization when provider transcripts exist ---
        # Providers (ElevenLabs, Vapi, Retell) already supply speaker-labeled segments.
        # PyAnnote diarization takes ~190s and is only needed when no segments exist.
        has_provider_segments = bool(db_seg_data)

        if has_provider_segments:
            logger.info(
                f"Skipping diarization — using {len(db_seg_data)} existing provider segments"
            )
            sorted_segs = sorted(db_seg_data, key=lambda s: s["start_sec"])
            latencies = []
            interruptions = 0
            total_speech_duration = 0.0
            total_words = 0

            for i, seg in enumerate(sorted_segs):
                start = seg["start_sec"]
                end = seg["end_sec"]
                total_speech_duration += max(0.0, end - start)
                if seg["text"]:
                    total_words += len(seg["text"].split())

                if i > 0:
                    prev_seg = sorted_segs[i - 1]
                    prev_end = prev_seg["end_sec"]
                    if start < prev_end and prev_seg["speaker"] != seg["speaker"]:
                        interruptions += 1
                    if prev_seg["speaker"] == "user" and seg["speaker"] == "agent":
                        pause = start - prev_end
                        if pause >= 0:
                            latencies.append(pause)

            avg_latency_sec = (sum(latencies) / len(latencies)) if latencies else 0.5
            latency_sec = avg_latency_sec
            dead_air_sec = max(0.0, call_duration - total_speech_duration)
            dead_air = round((dead_air_sec / call_duration) * 100.0, 2) if call_duration > 0 else 0.0
            speech_rate = int(round((total_words / (total_speech_duration / 60.0)))) if total_speech_duration > 0 else 140
            # No diarized segments to save downstream
            text_bearing_segs = []
        else:
            logger.info("No provider segments found — running PyAnnote diarization")
            diarizer = get_diarizer()
            segments = diarizer.diarize_mono(audio_np, sample_rate)
            text_bearing_segs = [s for s in segments if s.get("text")]

            if segments:
                latency_sec = calculate_turn_latency(segments)
                dead_air = calculate_dead_air(segments, call_duration)
                interruptions = calculate_interruptions(segments)
                speech_rate = calculate_speech_rate(segments)
            else:
                latency_sec = 0.5
                dead_air = 0.0
                interruptions = 0
                speech_rate = 140

        mos_score = score_voice_quality_nisqa(audio_np, sample_rate)
        transcript_text = " ".join([s["text"] for s in db_seg_data if s["text"]]) if db_seg_data else " ".join([seg.get("text", "") for seg in text_bearing_segs if "text" in seg])
        sentiment = score_sentiment_roberta(transcript_text)
        primary_emotion = None
        if sentiment:
            primary_emotion = max(sentiment.items(), key=lambda x: x[1])[0]
    except Exception as ml_err:
        logger.error(f"Error during ML audio analysis for {conversation_id}: {ml_err}")
        db = SessionLocal()
        try:
            conv = db.query(Conversation).filter(Conversation.id == str(conversation_id)).first()
            if conv:
                conv.status = "Error"
                db.commit()
        finally:
            db.close()
        raise ml_err

    # 3. Save Final Results in a Fresh Short DB Session
    db = SessionLocal()
    try:
        conversation = db.query(Conversation).filter(Conversation.id == str(conversation_id)).first()
        if not conversation:
            logger.error(f"Conversation {conversation_id} not found when committing evaluation.")
            return

        conversation.duration_sec = int(call_duration)
        conversation.latency_ms = int(latency_sec * 1000)
        conversation.dead_air_percent = dead_air
        conversation.interruptions = interruptions
        conversation.speech_rate_wpm = int(speech_rate)
        conversation.voice_quality = int((mos_score / 5.0) * 100)
        if primary_emotion:
            conversation.primary_emotion = primary_emotion

        health_score = 100 - (latency_sec * 10) - (dead_air * 2) - (interruptions * 5)
        conversation.health_score = max(0, min(100, int(round(health_score))))
        conversation.status = "Completed"
        conversation.raw_metrics_json = {
            "latency_sec": latency_sec,
            "mos_score": mos_score,
            "sentiment": sentiment
        }

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
            conv = db.query(Conversation).filter(Conversation.id == str(conversation_id)).first()
            if conv:
                conv.status = "Error"
                db.commit()
        except Exception:
            pass
        raise save_err
    finally:
        db.close()

