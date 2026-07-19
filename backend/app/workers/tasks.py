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

@celery_app.task(name="evaluate_audio")
def evaluate_audio(conversation_id: str, audio_url: str):
    """
    Downstream audio evaluation task.
    Currently runs as a stub that simulates ML pipeline analysis and completes the evaluation.
    """
    logger.info(f"Starting audio evaluation for conversation: {conversation_id} using audio: {audio_url}")
    db = SessionLocal()
    try:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            logger.error(f"Conversation {conversation_id} not found for evaluation.")
            return False

        # Simulate analysis calculations
        # We write realistic dummy scores so that ingestion produces immediate visual results in UI
        conversation.status = "Completed"
        conversation.health_score = 92
        conversation.latency_ms = 480
        conversation.dead_air_percent = 4.20
        conversation.interruptions = 1
        conversation.speech_rate_wpm = 138
        conversation.voice_quality = 94
        conversation.primary_emotion = "neutral"
        
        db.commit()
        logger.info(f"Successfully completed audio evaluation stub for conversation: {conversation_id}")
        return True

    except Exception as e:
        logger.exception(f"Exception occurred during evaluate_audio task")
        db.rollback()
        raise
    finally:
        db.close()
