import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json

from .loader import download_audio_stream, load_and_resample_audio, normalize_loudness
from .vad import SileroVADWrapper
from .diarizer import PyAnnoteDiarizer
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

# Initialize wrappers
vad_wrapper = SileroVADWrapper()
diarizer = PyAnnoteDiarizer()

def evaluate_audio(conversation_id: str, audio_url: str):
    """
    Main orchestration function for the audio analysis pipeline.
    """
    logger.info(f"Starting audio evaluation for conversation {conversation_id}")
    
    db: Session = SessionLocal()
    try:
        conversation = db.query(Conversation).filter(Conversation.id == str(conversation_id)).first()
        if not conversation:
            logger.error(f"Conversation {conversation_id} not found in database.")
            return
            
        # 1. Loader
        audio_buffer = download_audio_stream(audio_url)
        audio_np, sample_rate = load_and_resample_audio(audio_buffer)
        audio_np = normalize_loudness(audio_np, sample_rate)
        call_duration = len(audio_np) / sample_rate
            
        # Fetch existing transcript speech segments from database
        db_segments = db.query(SpeechSegment).filter(SpeechSegment.conversation_id == conversation.id).all()

        # 2. VAD & Diarization
        segments = diarizer.diarize_mono(audio_np, sample_rate)
        
        # 3. Extractors: Use existing DB segments if diarizer returns empty or no text
        text_bearing_segs = [s for s in segments if s.get("text")]
        
        if not text_bearing_segs and db_segments:
            sorted_segs = sorted(db_segments, key=lambda s: float(s.start_sec))
            latencies = []
            interruptions = 0
            total_speech_duration = 0.0
            total_words = 0

            for i, seg in enumerate(sorted_segs):
                start = float(seg.start_sec)
                end = float(seg.end_sec)
                total_speech_duration += max(0.0, end - start)
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

            avg_latency_sec = (sum(latencies) / len(latencies)) if latencies else 0.5
            latency_sec = avg_latency_sec
            dead_air_sec = max(0.0, call_duration - total_speech_duration)
            dead_air = round((dead_air_sec / call_duration) * 100.0, 2) if call_duration > 0 else 0.0
            speech_rate = int(round((total_words / (total_speech_duration / 60.0)))) if total_speech_duration > 0 else 140
        else:
            latency_sec = calculate_turn_latency(segments)
            dead_air = calculate_dead_air(segments, call_duration)
            interruptions = calculate_interruptions(segments)
            speech_rate = calculate_speech_rate(segments)
        
        # 4. ML Models
        mos_score = score_voice_quality_nisqa(audio_np, sample_rate)
        
        # Optional sentiment if transcript exists
        transcript_text = " ".join([seg.text for seg in db_segments if seg.text]) if db_segments else " ".join([seg.get("text", "") for seg in segments if "text" in seg])
        sentiment = score_sentiment_roberta(transcript_text)
        primary_emotion = None
        if sentiment:
            primary_emotion = max(sentiment.items(), key=lambda x: x[1])[0]
        
        # 5. Database Updates
        conversation.duration_sec = int(call_duration)
        conversation.latency_ms = int(latency_sec * 1000)
        conversation.dead_air_percent = dead_air
        conversation.interruptions = interruptions
        conversation.speech_rate_wpm = int(speech_rate)
        
        # NISQA returns 1.0 to 5.0, voice_quality DB field expects 0-100
        conversation.voice_quality = int((mos_score / 5.0) * 100)
        if primary_emotion:
            conversation.primary_emotion = primary_emotion
            
        # Simple health score heuristic
        health_score = 100 - (latency_sec * 10) - (dead_air * 2) - (interruptions * 5)
        conversation.health_score = max(0, min(100, int(round(health_score))))
        
        conversation.status = "Completed"
        conversation.raw_metrics_json = {
            "latency_sec": latency_sec,
            "mos_score": mos_score,
            "sentiment": sentiment
        }
        
        # Save segments ONLY if new text-bearing segments are produced
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
        logger.info(f"Evaluation completed for {conversation_id}")
        
    except Exception as e:
        logger.error(f"Error evaluating audio for {conversation_id}: {e}")
        db.rollback()
        # Attempt to set error status
        try:
            conv = db.query(Conversation).filter(Conversation.id == str(conversation_id)).first()
            if conv:
                conv.status = "Error"
                db.commit()
        except Exception as inner_e:
            logger.error(f"Could not set Error status: {inner_e}")
    finally:
        db.close()
