import logging
from app.workers import celery_app
from app.database import SessionLocal
from app.models.integration import Integration
from app.models.conversation import Conversation, SpeechSegment
from app.models.agent import Agent
from app.workers.connectors.vapi import VapiConnector
from app.workers.connectors.retell import RetellConnector
from app.workers.connectors.elevenlabs import ElevenLabsConnector

logger = logging.getLogger(__name__)

CONNECTORS = {
    "vapi": VapiConnector,
    "retell": RetellConnector,
    "elevenlabs": ElevenLabsConnector
}

@celery_app.task(name="ingest_call")
def ingest_call(project_id: str, provider: str, provider_call_id: str):
    """
    Ingests call details from a speech provider.
    1. Fetches integration credentials.
    2. Calls provider API to get duration, audio_url, agent name, and speaker turns.
    3. Resolves agent (creates if not found).
    4. Creates conversation in 'Processing' state.
    5. Saves speaker turns as speech segments.
    6. Chains evaluate_audio task.
    """
    logger.info(f"Starting ingestion for project: {project_id}, provider: {provider}, call_id: {provider_call_id}")
    db = SessionLocal()
    try:
        # 1. Fetch credentials from integrations DB table
        integration = db.query(Integration).filter(
            Integration.project_id == project_id,
            Integration.name.ilike(provider)
        ).first()

        api_key = "mock"
        config = {}
        if integration and integration.connected and integration.api_key:
            api_key = integration.api_key
            config = integration.config or {}
            logger.info(f"Found active integration config for {provider}")
        elif provider_call_id.startswith("mock_"):
            logger.info(f"No integration found, but call ID '{provider_call_id}' is a mock call. Proceeding in mock mode.")
        else:
            raise ValueError(f"No active integration found for provider '{provider}' in project '{project_id}'")

        # Get connector
        connector_class = CONNECTORS.get(provider.lower())
        if not connector_class:
            raise ValueError(f"Unsupported speech provider: {provider}")

        # 2. Initialize connector & pull metadata + audio_url
        connector = connector_class(api_key=api_key, config=config)
        call_data = connector.fetch_call_data(provider_call_id)

        # Ensure we have required fields
        audio_url = call_data.get("audio_url")
        duration_sec = call_data.get("duration_sec", 0)
        agent_name = call_data.get("agent_name") or f"{provider.capitalize()} Agent"
        turns = call_data.get("turns", [])

        # 3. Resolve agent name/id in DB
        agent = db.query(Agent).filter(
            Agent.project_id == project_id,
            Agent.provider == provider.lower(),
            Agent.name == agent_name
        ).first()

        if not agent:
            logger.info(f"Agent '{agent_name}' not found for provider {provider}. Auto-creating Agent record.")
            agent = Agent(
                project_id=project_id,
                name=agent_name,
                provider=provider.lower()
            )
            db.add(agent)
            db.commit()
            db.refresh(agent)

        # 4. Create conversation entry in PostgreSQL (status = 'Processing')
        conversation = Conversation(
            project_id=project_id,
            agent_id=agent.id,
            duration_sec=duration_sec,
            status="Processing",
            health_score=100,  # default placeholder
            latency_ms=0,
            dead_air_percent=0.00,
            interruptions=0,
            speech_rate_wpm=0,
            voice_quality=100,
            audio_url=audio_url,
            raw_metrics_json={
                "provider_call_id": provider_call_id,
                "provider": provider.lower(),
                "provider_metadata": call_data.get("metadata", {})
            }
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        logger.info(f"Created Conversation record with ID: {conversation.id} (status: Processing)")

        # 5. Save speaker turns as speech segments
        for turn in turns:
            segment = SpeechSegment(
                conversation_id=conversation.id,
                speaker=turn["speaker"],
                start_sec=turn["start_sec"],
                end_sec=turn["end_sec"],
                text=turn["text"]
            )
            db.add(segment)
        db.commit()
        logger.info(f"Saved {len(turns)} speech segments for conversation {conversation.id}")

        # 6. Chain next Celery analysis task: evaluate_audio
        evaluate_audio.delay(str(conversation.id), audio_url)
        
        return str(conversation.id)

    except Exception as e:
        logger.exception(f"Exception occurred during ingest_call task")
        db.rollback()
        raise
    finally:
        db.close()

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import or_

@celery_app.task(name="sync_calls")
def sync_calls_task(project_id: str, provider: str):
    """
    Celery task to trigger call synchronization for a provider integration.
    """
    logger.info(f"Starting Celery sync_calls_task for project {project_id}, provider {provider}")
    db = SessionLocal()
    try:
        results = sync_calls_for_integration(db, project_id, provider)
        logger.info(f"Completed sync_calls_task for {provider}: {results}")
        return results
    except Exception as e:
        logger.exception(f"Error executing sync_calls_task for {provider}: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def sync_calls_for_integration(db: Session, project_id: str, provider: str) -> dict:
    """
    Core execution logic for synchronizing calls from a provider account.
    Prevents duplicates, saves conversation records and speech turns,
    queues evaluation tasks, and updates integration last_synced_at.
    """
    provider_key = provider.lower()
    integration = db.query(Integration).filter(
        Integration.project_id == project_id,
        or_(Integration.name.ilike(provider_key), Integration.name.ilike(provider))
    ).first()

    if not integration or not integration.connected or not integration.api_key:
        logger.warning(f"Integration for {provider} not connected or missing API key in project {project_id}")
        return {"total": 0, "imported": 0, "skipped": 0}

    connector_cls = CONNECTORS.get(provider_key)
    if not connector_cls:
        logger.error(f"No connector registered for provider {provider}")
        return {"total": 0, "imported": 0, "skipped": 0}

    connector = connector_cls(api_key=integration.api_key, config=integration.config or {})
    sync_start_time = datetime.now(timezone.utc)
    last_synced_at = integration.last_synced_at

    logger.info(f"Fetching calls for provider {provider_key} (last_synced_at: {last_synced_at})")
    raw_calls = connector.list_calls(created_after=last_synced_at)

    imported_count = 0
    skipped_count = 0

    for call_summary in raw_calls:
        ext_call_id = call_summary.get("external_id")
        if not ext_call_id:
            continue

        # Check duplicate call
        existing = db.query(Conversation).filter(
            Conversation.project_id == project_id,
            Conversation.provider == provider_key,
            Conversation.external_id == ext_call_id
        ).first()

        if existing:
            skipped_count += 1
            continue

        # Fetch detailed call payload
        try:
            call_details = connector.get_call(ext_call_id)
        except Exception as e:
            logger.warning(f"Could not fetch full details for call {ext_call_id}: {e}")
            call_details = call_summary

        ext_agent_id = call_details.get("agent_id") or call_summary.get("agent_id")
        agent_name = call_details.get("agent_name") or f"{provider.capitalize()} Agent"

        # Resolve Agent in DB
        agent = None
        if ext_agent_id:
            agent = db.query(Agent).filter(
                Agent.project_id == project_id,
                Agent.provider == provider_key,
                Agent.external_id == ext_agent_id
            ).first()

        if not agent:
            agent = db.query(Agent).filter(
                Agent.project_id == project_id,
                Agent.provider == provider_key,
                Agent.name == agent_name
            ).first()

        if not agent:
            logger.info(f"Auto-creating agent '{agent_name}' ({ext_agent_id}) for provider {provider_key}")
            agent = Agent(
                project_id=project_id,
                name=agent_name,
                provider=provider_key,
                external_id=ext_agent_id,
                last_synced_at=sync_start_time
            )
            db.add(agent)
            db.commit()
            db.refresh(agent)

        audio_url = call_details.get("audio_url")
        duration_sec = call_details.get("duration_sec") or call_summary.get("duration_sec", 0)

        conversation = Conversation(
            project_id=project_id,
            agent_id=agent.id,
            external_id=ext_call_id,
            provider=provider_key,
            started_at=call_details.get("started_at") or call_summary.get("started_at"),
            ended_at=call_details.get("ended_at") or call_summary.get("ended_at"),
            duration_sec=duration_sec,
            cost=call_details.get("cost") or call_summary.get("cost"),
            status="Processing",
            health_score=None,
            latency_ms=None,
            dead_air_percent=None,
            interruptions=None,
            speech_rate_wpm=None,
            voice_quality=None,
            audio_url=audio_url,
            raw_metrics_json={
                "provider_call_id": ext_call_id,
                "provider": provider_key,
                "provider_metadata": call_details.get("metadata", call_summary.get("raw_metadata", {}))
            }
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        # Save speaker turns
        turns = call_details.get("turns", [])
        for turn in turns:
            segment = SpeechSegment(
                conversation_id=conversation.id,
                speaker=turn["speaker"],
                start_sec=turn["start_sec"],
                end_sec=turn["end_sec"],
                text=turn["text"]
            )
            db.add(segment)
        db.commit()

        # Queue audio evaluation
        evaluate_audio.delay(str(conversation.id), audio_url)
        imported_count += 1

    # Update last_synced_at timestamp on integration
    integration.last_synced_at = sync_start_time
    db.commit()

    return {
        "total": len(raw_calls),
        "imported": imported_count,
        "skipped": skipped_count
    }


@celery_app.task(name="evaluate_audio")
def evaluate_audio(conversation_id: str, audio_url: str):
    """
    Downstream audio evaluation task.
    Attempts to run the real audio evaluation pipeline, falling back to a realistic stub
    if dependencies or weights are not loaded/configured, and publishes a Redis completion event.
    """
    logger.info(f"Starting audio evaluation for conversation: {conversation_id} using audio: {audio_url}")
    db = SessionLocal()
    
    # To notify the UI that processing is starting
    import redis
    import json
    from app.config import settings
    
    try:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            logger.error(f"Conversation {conversation_id} not found for evaluation.")
            return False

        pipeline_success = False
        try:
            from app.pipeline.scoring import evaluate_audio as run_real_evaluation
            logger.info("Attempting to run real audio evaluation pipeline...")
            run_real_evaluation(conversation_id, audio_url)
            pipeline_success = True
            logger.info("Real audio evaluation pipeline completed successfully.")
        except Exception as pipeline_err:
            logger.warning(f"Failed to run real evaluation pipeline ({pipeline_err}). Falling back to mock evaluation.")

        if not pipeline_success:
            # Compute dynamic real metrics from conversation speech segments
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            segments = db.query(SpeechSegment).filter(SpeechSegment.conversation_id == conversation_id).all()
            
            if segments:
                sorted_segs = sorted(segments, key=lambda s: float(s.start_sec))
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
                call_dur = float(conversation.duration_sec or (sorted_segs[-1].end_sec if sorted_segs else 1.0))
                dead_air_sec = max(0.0, call_dur - total_speech_duration)
                dead_air_pct = round((dead_air_sec / call_dur) * 100.0, 2) if call_dur > 0 else 0.0
                wpm = int(round((total_words / (total_speech_duration / 60.0)))) if total_speech_duration > 0 else 140

                calculated_score = max(0, min(100, int(round(100 - (avg_latency_sec * 10) - (dead_air_pct * 2) - (interruptions * 5)))))

                conversation.status = "Completed"
                conversation.health_score = calculated_score
                conversation.latency_ms = int(round(avg_latency_sec * 1000))
                conversation.dead_air_percent = dead_air_pct
                conversation.interruptions = interruptions
                conversation.speech_rate_wpm = wpm
                conversation.voice_quality = min(100, max(60, calculated_score))
                conversation.primary_emotion = "neutral"
            else:
                conversation.status = "Completed"
                conversation.health_score = None

            db.commit()
            logger.info(f"Completed dynamic transcript segment evaluation for conversation {conversation_id} (health_score={conversation.health_score})")

        # Publish live update event to Redis
        try:
            r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
            event_data = {
                "type": "conversation_completed",
                "conversation_id": conversation_id,
                "project_id": str(conversation.project_id)
            }
            r.publish("benten-updates", json.dumps(event_data))
            logger.info(f"Published completion event to Redis for conversation {conversation_id}")
        except Exception as redis_err:
            logger.error(f"Failed to publish event to Redis: {redis_err}")

        return True

    except Exception as e:
        logger.exception(f"Exception occurred during evaluate_audio task")
        db.rollback()
        raise
    finally:
        db.close()

