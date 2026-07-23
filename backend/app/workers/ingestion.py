import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.workers.connectors import CONNECTORS
from app.models.integration import Integration
from app.models.agent import Agent
from app.models.conversation import Conversation, SpeechSegment
from app.api.security_crypto import decrypt_secret

logger = logging.getLogger(__name__)


def process_call_ingestion(db: Session, project_id: str, provider: str, provider_call_id: str) -> tuple[str, str]:
    """
    Ingests call details from a speech provider API.
    Returns a tuple of (conversation_id, audio_url).
    """
    provider_key = provider.lower()

    existing = db.query(Conversation).filter(
        Conversation.project_id == project_id,
        Conversation.provider == provider_key,
        Conversation.external_id == provider_call_id
    ).first()

    if existing:
        logger.info(f"Call Already ingested: {provider_call_id}. Skipping.")
        return str(existing.id), existing.audio_url or ""

    integration = db.query(Integration).filter(
        Integration.project_id == project_id,
        Integration.name.ilike(provider)
    ).first()

    api_key = "mock"
    config = {}
    if integration and integration.connected and integration.api_key:
        api_key = decrypt_secret(integration.api_key) or "mock"
        config = integration.config or {}
    elif not provider_call_id.startswith("mock_"):
        raise ValueError(f"No active integration found for provider '{provider}' in project '{project_id}'")

    connector_class = CONNECTORS.get(provider_key)
    if not connector_class:
        raise ValueError(f"Unsupported speech provider: {provider}")

    connector = connector_class(api_key=api_key, config=config)
    call_data = connector.fetch_call_data(provider_call_id)

    audio_url = call_data.get("audio_url") or ""
    duration_sec = call_data.get("duration_sec", 0)
    agent_name = call_data.get("agent_name") or f"{provider.capitalize()} Agent"
    turns = call_data.get("turns", [])

    agent = db.query(Agent).filter(
        Agent.project_id == project_id,
        Agent.provider == provider_key,
        Agent.name == agent_name
    ).first()

    if not agent:
        agent = Agent(
            project_id=project_id,
            name=agent_name,
            provider=provider_key
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)

    conversation = Conversation(
        project_id=project_id,
        agent_id=agent.id,
        external_id=provider_call_id,
        provider=provider_key,
        duration_sec=duration_sec,
        status="Processing",
        health_score=100,
        latency_ms=0,
        dead_air_percent=0.00,
        interruptions=0,
        speech_rate_wpm=0,
        voice_quality=100,
        audio_url=audio_url,
        raw_metrics_json={
            "provider_call_id": provider_call_id,
            "provider": provider_key,
            "provider_metadata": call_data.get("metadata", {})
        }
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

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

    return str(conversation.id), audio_url


def sync_calls_for_integration(db: Session, project_id: str, provider: str) -> dict:
    """
    Synchronizes new calls from provider account.
    """
    provider_key = provider.lower()
    integration = db.query(Integration).filter(
        Integration.project_id == project_id,
        or_(Integration.name.ilike(provider_key), Integration.name.ilike(provider))
    ).first()

    if not integration or not integration.connected or not integration.api_key:
        logger.warning(f"Integration config missing or disconnected for {provider} in project {project_id}")
        return {"total": 0, "imported": 0, "skipped": 0}

    connector_cls = CONNECTORS.get(provider_key)
    if not connector_cls:
        logger.error(f"Connector unregistered for provider {provider}")
        return {"total": 0, "imported": 0, "skipped": 0}

    decrypted_key = decrypt_secret(integration.api_key) or integration.api_key
    connector = connector_cls(api_key=decrypted_key, config=integration.config or {})
    sync_start_time = datetime.now(timezone.utc)
    last_synced_at = integration.last_synced_at

    raw_calls = connector.list_calls(created_after=last_synced_at)
    imported_count = 0
    skipped_count = 0

    for call_summary in raw_calls:
        ext_call_id = call_summary.get("external_id")
        if not ext_call_id:
            continue

        existing = db.query(Conversation).filter(
            Conversation.project_id == project_id,
            Conversation.provider == provider_key,
            Conversation.external_id == ext_call_id
        ).first()

        if existing:
            skipped_count += 1
            continue

        try:
            call_details = connector.get_call(ext_call_id)
        except Exception as e:
            logger.warning(f"Could not fetch full details for call {ext_call_id}: {e}")
            call_details = call_summary

        ext_agent_id = call_details.get("agent_id") or call_summary.get("agent_id")
        agent_name = call_details.get("agent_name") or f"{provider.capitalize()} Agent"

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

        # Trigger evaluation asynchronously using Celery name dispatch
        from app.workers import celery_app
        celery_app.send_task("evaluate_audio", args=[str(conversation.id), audio_url])
        imported_count += 1

    integration.last_synced_at = sync_start_time
    db.commit()

    return {
        "total": len(raw_calls),
        "imported": imported_count,
        "skipped": skipped_count
    }
