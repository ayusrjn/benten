import pytest
from unittest.mock import patch, MagicMock
from app.workers.connectors.bolna import BolnaConnector
from app.services.project_service import PROVIDER_KEY_TO_NAME

def test_bolna_provider_name_registration():
    assert "bolna" in PROVIDER_KEY_TO_NAME
    assert PROVIDER_KEY_TO_NAME["bolna"] == "Bolna"

@patch("requests.get")
def test_bolna_connector_verify_key_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response
    
    connector = BolnaConnector(api_key="test_key")
    success, msg = connector.verify_key()
    assert success is True
    assert "Successfully connected" in msg
    mock_get.assert_called_once_with(
        "https://api.bolna.ai/v2/agent/all",
        headers={"Authorization": "Bearer test_key"},
        timeout=10
    )

@patch("requests.get")
def test_bolna_connector_verify_key_unauthorized(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_get.return_value = mock_response
    
    connector = BolnaConnector(api_key="invalid_key")
    success, msg = connector.verify_key()
    assert success is False
    assert "Invalid Bolna API key" in msg

@patch("requests.get")
def test_bolna_connector_list_agents(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"agent_id": "agent-123", "agent_name": "Sales Rep", "status": "active", "created_at": "2026-05-01T12:00:00Z"}
    ]
    mock_get.return_value = mock_response
    
    connector = BolnaConnector(api_key="test_key")
    agents = connector.list_agents()
    assert len(agents) == 1
    assert agents[0]["external_id"] == "agent-123"
    assert agents[0]["name"] == "Sales Rep"
    assert agents[0]["description"] == "Status: active"
    assert agents[0]["created_at"] == "2026-05-01T12:00:00Z"

@patch("requests.get")
def test_bolna_connector_get_call_with_plain_transcript(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "execution_id": "exec-abc",
        "agent_id": "agent-123",
        "agent_name": "Sales Rep",
        "recording_url": "https://api.bolna.ai/recording/exec-abc.mp3",
        "duration": 30,
        "created_at": "2026-05-01T12:05:00Z",
        "cost": 0.05,
        "transcript": "Agent: Hello there!\nUser: Hi, how are you?",
    }
    mock_get.return_value = mock_response
    
    connector = BolnaConnector(api_key="test_key")
    call_data = connector.get_call("exec-abc")
    
    assert call_data["external_id"] == "exec-abc"
    assert call_data["agent_name"] == "Sales Rep"
    assert call_data["audio_url"] == "https://api.bolna.ai/recording/exec-abc.mp3"
    assert call_data["duration_sec"] == 30
    assert len(call_data["turns"]) == 2
    assert call_data["turns"][0]["speaker"] == "agent"
    assert call_data["turns"][0]["text"] == "Hello there!"
    assert call_data["turns"][1]["speaker"] == "user"
    assert call_data["turns"][1]["text"] == "Hi, how are you?"

@patch("requests.get")
def test_bolna_connector_list_calls_specific_agent(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"execution_id": "exec-abc", "created_at": "2026-05-01T12:05:00Z", "duration": 45, "cost": 0.07, "status": "completed"}
    ]
    mock_get.return_value = mock_response
    
    connector = BolnaConnector(api_key="test_key")
    calls = connector.list_calls(agent_id="agent-123")
    assert len(calls) == 1
    assert calls[0]["external_id"] == "exec-abc"
    assert calls[0]["agent_id"] == "agent-123"
    assert calls[0]["duration_sec"] == 45
    assert calls[0]["status"] == "completed"

@patch("requests.get")
def test_bolna_connector_list_calls_dict_format(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {
                "id": "exec-xyz",
                "created_at": "2026-05-01T12:05:00Z",
                "conversation_duration": 60,
                "total_cost": 0.10,
                "status": "completed"
            }
        ]
    }
    mock_get.return_value = mock_response
    
    connector = BolnaConnector(api_key="test_key")
    calls = connector.list_calls(agent_id="agent-123")
    assert len(calls) == 1
    assert calls[0]["external_id"] == "exec-xyz"
    assert calls[0]["agent_id"] == "agent-123"
    assert calls[0]["duration_sec"] == 60
    assert calls[0]["status"] == "completed"

