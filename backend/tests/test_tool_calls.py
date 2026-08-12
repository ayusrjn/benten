import pytest
from datetime import datetime, timezone
from app.workers.connectors.retell import RetellConnector
from app.workers.connectors.bolna import BolnaConnector
from app.workers.connectors.elevenlabs import ElevenLabsConnector

def test_retell_tool_call_extraction():
    connector = RetellConnector(api_key="test_key")
    
    mock_data = {
        "transcript_with_tool_calls": [
            {
                "role": "agent",
                "content": "Hello!"
            },
            {
                "role": "tool_call",
                "tool_call_id": "call_1",
                "name": "check_status",
                "arguments": "{\"id\": 123}"
            },
            {
                "role": "tool_result",
                "tool_call_id": "call_1",
                "content": "{\"status\": \"ok\"}"
            }
        ],
        "latency": {
            "tool_calls": [
                {
                    "name": "check_status",
                    "latency": 1.25
                }
            ]
        }
    }
    
    turns = [
        {"speaker": "agent", "start_sec": 0.0, "end_sec": 2.0, "text": "Hello!"}
    ]
    
    tool_calls = connector._extract_tool_calls(mock_data, turns)
    assert len(tool_calls) == 1
    assert tool_calls[0]["id"] == "call_1"
    assert tool_calls[0]["name"] == "check_status"
    assert tool_calls[0]["arguments"] == "{\"id\": 123}"
    assert tool_calls[0]["result"] == "{\"status\": \"ok\"}"
    assert tool_calls[0]["latency_ms"] == 1250


def test_bolna_tool_call_extraction():
    connector = BolnaConnector(api_key="test_key")
    
    mock_data = {
        "steps": [
            {
                "type": "tool",
                "id": "step_abc",
                "name": "calculate_tax",
                "arguments": {"amount": 100},
                "start_time_sec": 5.0,
                "latency_ms": 780,
                "result": {"tax": 8.5}
            }
        ],
        "latency_data": {
            "calculate_tax": 0.78
        }
    }
    
    tool_calls = connector._extract_tool_calls(mock_data)
    assert len(tool_calls) == 1
    assert tool_calls[0]["id"] == "step_abc"
    assert tool_calls[0]["name"] == "calculate_tax"
    assert tool_calls[0]["latency_ms"] == 780
    assert tool_calls[0]["start_time_sec"] == 5.0


def test_elevenlabs_tool_call_extraction():
    connector = ElevenLabsConnector(api_key="test_key")
    
    mock_data = {
        "transcript": [
            {
                "role": "agent",
                "message": "Let me look that up.",
                "time_in_call_secs": 1.0
            },
            {
                "tool_call": {
                    "id": "tc_123",
                    "name": "lookup_user",
                    "arguments": {"user_id": "abc"}
                },
                "time_in_call_secs": 2.5
            },
            {
                "tool_result": {
                    "id": "tc_123",
                    "name": "lookup_user",
                    "result": {"name": "Test User"},
                    "latency_ms": 1500
                },
                "time_in_call_secs": 4.0
            }
        ]
    }
    
    tool_calls = connector._extract_tool_calls(mock_data)
    assert len(tool_calls) == 1
    assert tool_calls[0]["id"] == "tc_123"
    assert tool_calls[0]["name"] == "lookup_user"
    assert tool_calls[0]["latency_ms"] == 1500
    assert tool_calls[0]["result"] == {"name": "Test User"}


from unittest.mock import patch, MagicMock

@patch("requests.get")
def test_retell_cost_calculation(mock_get):
    connector = RetellConnector(api_key="test_key")
    
    # Test case 1: call_cost is direct number (cents)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "call_id": "c1",
        "agent_id": "a1",
        "call_cost": 15.5,  # 15.5 cents
        "duration_ms": 10000,
        "transcript_object": []
    }
    mock_get.return_value = mock_response
    
    res = connector.fetch_call_data("c1")
    assert res["cost"] == 0.155

    # Test case 2: call_cost is dictionary container with combined_cost
    mock_response.json.return_value = {
        "call_id": "c1",
        "agent_id": "a1",
        "call_cost": {
            "combined_cost": 42.0
        },
        "duration_ms": 10000,
        "transcript_object": []
    }
    res = connector.fetch_call_data("c1")
    assert res["cost"] == 0.420

    # Test case 3: call_cost is dictionary container with product_costs list
    mock_response.json.return_value = {
        "call_id": "c1",
        "agent_id": "a1",
        "call_cost": {
            "product_costs": [
                {"product": "elevenlabs_tts", "cost": 10.0},
                {"product": "llm", "cost": 5.5}
            ]
        },
        "duration_ms": 10000,
        "transcript_object": []
    }
    res = connector.fetch_call_data("c1")
    assert res["cost"] == 0.155


@patch("requests.get")
def test_elevenlabs_cost_calculation(mock_get):
    connector = ElevenLabsConnector(api_key="test_key")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "conversation_id": "conv_1",
        "agent_id": "agent_1",
        "call_duration_secs": 120,
        "cost": 1500,
        "start_time_unix_secs": 1714423232,
        "transcript": []
    }
    
    audio_response = MagicMock()
    audio_response.status_code = 404
    
    mock_get.side_effect = [mock_response, audio_response]
    
    res = connector.fetch_call_data("conv_1")
    assert res["cost"] == 1500 * 0.00015


