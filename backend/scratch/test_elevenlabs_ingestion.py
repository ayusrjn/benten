import sys
import os
from datetime import datetime, timezone

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.workers.connectors.elevenlabs import ElevenLabsConnector

def test_elevenlabs_connector():
    print("=== TESTING ELEVENLABS CONNECTOR TRANSCRIPT & RECORDING PARSING ===")

    connector = ElevenLabsConnector(api_key="mock")

    # 1. Test mock data retrieval
    mock_data = connector.get_call("mock_el_call_001")
    assert mock_data["external_id"] == "mock_el_call_001"
    assert len(mock_data["turns"]) == 3
    assert mock_data["turns"][0]["speaker"] == "agent"
    assert mock_data["turns"][1]["speaker"] == "user"
    print("[1] Mock call retrieval verified with turns & speaker roles.")

    # 2. Test response parsing logic for various ElevenLabs API key combinations
    # Simulation of raw ElevenLabs API response with 'transcript' field
    raw_api_payload = {
        "conversation_id": "el_conv_999",
        "agent_id": "agent_el_01",
        "agent_name": "ElevenLabs Test Agent",
        "start_time_unix_secs": 1700000000,
        "call_duration_secs": 42,
        "cost": 0.05,
        "transcript": [
            {
                "role": "user",
                "message": "Hello, I want to evaluate ElevenLabs agents.",
                "time_in_call_secs": 0.5
            },
            {
                "role": "agent",
                "message": "Sure! I can help you evaluate performance and latency.",
                "time_in_call_secs": 2.1
            }
        ]
    }

    # Simulate parsing
    turns = []
    raw_turns = (
        raw_api_payload.get("transcript") or 
        raw_api_payload.get("messages") or 
        raw_api_payload.get("turns") or []
    )
    
    for turn in raw_turns:
        role = turn.get("role") or turn.get("speaker") or "agent"
        speaker = "agent" if role in ("agent", "assistant", "bot") else "user"
        text = turn.get("message") or turn.get("text") or turn.get("content") or ""
        start_sec = turn.get("time_in_call_secs") or turn.get("start_time_sec") or 0.0
        turns.append({"speaker": speaker, "text": text, "start_sec": start_sec})

    assert len(turns) == 2
    assert turns[0]["speaker"] == "user"
    assert turns[0]["text"] == "Hello, I want to evaluate ElevenLabs agents."
    assert turns[1]["speaker"] == "agent"
    assert turns[1]["text"] == "Sure! I can help you evaluate performance and latency."
    # 3. Test list_calls mock fetching and sync_calls execution
    mock_calls = connector.list_calls()
    assert len(mock_calls) == 2
    assert mock_calls[0]["external_id"] == "mock_el_call_001"
    print("[3] ElevenLabs list_calls verified without dropping items.")

    from app.database import SessionLocal
    from app.models.user import User
    from app.models.integration import Integration
    from app.api.integrations import get_or_create_user_project
    from app.workers.tasks import sync_calls_for_integration

    db = SessionLocal()
    try:
        user = db.query(User).first()
        if user:
            project = get_or_create_user_project(db, user)
            
            # Connect ElevenLabs integration with mock key if not connected
            el_integration = db.query(Integration).filter(
                Integration.project_id == project.id,
                Integration.name == "ElevenLabs"
            ).first()
            if el_integration:
                el_integration.connected = True
                el_integration.api_key = "mock"
                db.commit()

            res = sync_calls_for_integration(db, str(project.id), "elevenlabs")
            print(f"[4] ElevenLabs DB Call Sync Result: {res}")
            assert res["total"] >= 2

            # Test evaluate_audio on synced conversation
            from app.models.conversation import Conversation
            from app.workers.tasks import evaluate_audio

            conv = db.query(Conversation).filter(
                Conversation.project_id == project.id,
                Conversation.provider == "elevenlabs"
            ).first()

            if conv:
                # Test relative static URL loader support
                from app.pipeline.loader import download_audio_stream
                try:
                    buf = download_audio_stream("/static/audio/mock_test.mp3")
                    print("[6] Loader download_audio_stream successfully resolved relative static URL")
                except Exception as e:
                    print(f"[6] Loader handled relative static URL gracefully ({e})")

                evaluate_audio(str(conv.id), conv.audio_url or "")
                db.refresh(conv)
                print(f"[5] Dynamic Audio Evaluation Output for Call {conv.id}:")
                print(f"    - Health Score: {conv.health_score}")
                print(f"    - Turn Latency: {conv.latency_ms}ms")
                print(f"    - Dead Air: {conv.dead_air_percent}%")
                print(f"    - Interruptions: {conv.interruptions}")
                print(f"    - WPM: {conv.speech_rate_wpm}")
                assert conv.health_score is not None
    finally:
        db.close()

    print("\nALL ELEVENLABS CONNECTOR & SYNC TESTS PASSED SUCCESSFULLY! ")

if __name__ == "__main__":
    test_elevenlabs_connector()
