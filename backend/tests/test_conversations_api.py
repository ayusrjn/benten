from datetime import datetime, timezone
import pytest
from fastapi import HTTPException
from app.services.project_service import ProjectService
from app.models.agent import Agent
from app.models.conversation import Conversation, SpeechSegment
from app.api.stream import verify_stream_token
from app.api.security import create_access_token


def test_conversations_api_list(client, auth_headers, db_session, test_user):
    project = ProjectService.get_or_create_user_project(db_session, test_user)

    agent = Agent(
        project_id=project.id,
        name="Test Agent",
        provider="vapi"
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)

    now = datetime.now(timezone.utc)

    conv = Conversation(
        project_id=project.id,
        agent_id=agent.id,
        duration_sec=60,
        status="Completed",
        health_score=95,
        latency_ms=300,
        dead_air_percent=2.5,
        interruptions=1,
        speech_rate_wpm=150,
        voice_quality=90,
        provider="vapi",
        created_at=now
    )
    db_session.add(conv)
    db_session.commit()
    db_session.refresh(conv)

    seg = SpeechSegment(
        conversation_id=conv.id,
        speaker="agent",
        start_sec=0.0,
        end_sec=3.5,
        text="Hello, welcome to support.",
        created_at=now
    )
    db_session.add(seg)
    db_session.commit()

    res = client.get("/api/v1/conversations", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["agentName"] == "Test Agent"
    assert data[0]["score"] == 95


def test_stream_token_validation(test_user):
    valid_token = create_access_token(data={"sub": str(test_user.id)})
    # Valid token passes verification without exception
    verify_stream_token(valid_token)

    # Invalid token raises 401 HTTPException
    with pytest.raises(HTTPException) as exc_info:
        verify_stream_token("invalid_garbage_token")
    assert exc_info.value.status_code == 401
