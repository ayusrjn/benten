import requests
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.workers.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

class VapiConnector(BaseConnector):
    """
    Connector for Vapi.ai API.
    Retrieves assistants, call summaries, full call recordings, and speaker turns.
    """
    def verify_key(self) -> tuple[bool, str]:
        if self.api_key == "mock" or self.api_key.startswith("mock_"):
            return True, "Mock Vapi API key valid"
        try:
            url = "https://api.vapi.ai/assistant"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            res = requests.get(url, headers=headers, params={"limit": 1}, timeout=10)
            if res.status_code == 200:
                return True, "Successfully connected to Vapi API"
            elif res.status_code in (401, 403):
                return False, "Invalid Vapi API key"
            return False, f"Vapi API returned status code {res.status_code}"
        except Exception as e:
            return False, f"Failed to connect to Vapi: {str(e)}"

    def _extract_tool_calls(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        tool_calls_map = {}
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            role = msg.get("role")
            msg_time = msg.get("time") or msg.get("timestamp")
            if msg_time is None and msg.get("secondsFromStart") is not None:
                msg_time = float(msg["secondsFromStart"]) * 1000.0

            if role == "tool-call":
                t_calls = msg.get("toolCalls") or []
                for tc in t_calls:
                    if not isinstance(tc, dict):
                        continue
                    tc_id = tc.get("id")
                    func_data = tc.get("function") or {}
                    name = func_data.get("name")
                    arguments = func_data.get("arguments")
                    
                    tool_calls_map[tc_id] = {
                        "id": tc_id,
                        "name": name,
                        "arguments": arguments,
                        "start_time": msg_time,
                        "start_time_sec": msg.get("secondsFromStart"),
                        "end_time": None,
                        "latency_ms": None,
                        "result": None,
                        "error": None
                    }

            elif role == "tool-call-result":
                tc_id = msg.get("toolCallId")
                result = msg.get("result")
                error = msg.get("error")
                name = msg.get("name")
                
                if tc_id in tool_calls_map:
                    entry = tool_calls_map[tc_id]
                    entry["end_time"] = msg_time
                    entry["result"] = result
                    entry["error"] = error
                    if entry["start_time"] is not None and msg_time is not None:
                        entry["latency_ms"] = int(msg_time - entry["start_time"])
                else:
                    tool_calls_map[tc_id] = {
                        "id": tc_id,
                        "name": name,
                        "arguments": None,
                        "start_time": None,
                        "start_time_sec": msg.get("secondsFromStart"),
                        "end_time": msg_time,
                        "latency_ms": None,
                        "result": result,
                        "error": error
                    }

        result_list = list(tool_calls_map.values())
        result_list.sort(key=lambda x: (x["start_time"] or 0.0, x["start_time_sec"] or 0.0))
        for entry in result_list:
            entry.pop("start_time", None)
            entry.pop("end_time", None)
        return result_list

    def get_call(self, call_id: str) -> Dict[str, Any]:
        if self.api_key == "mock" or call_id.startswith("mock_"):
            return self._get_mock_data(call_id)

        url = f"https://api.vapi.ai/call/{call_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        duration_sec = int(data.get("duration", 0))
        audio_url = data.get("recordingUrl")
        assistant = data.get("assistant", {})
        agent_name = assistant.get("name") or data.get("assistantId") or "Vapi Agent"
        agent_id = data.get("assistantId") or assistant.get("id")
        
        # Timestamps and cost
        started_at = None
        if data.get("createdAt"):
            try:
                started_at = datetime.fromisoformat(data.get("createdAt").replace("Z", "+00:00"))
            except Exception:
                pass
                
        ended_at = None
        if data.get("endedAt"):
            try:
                ended_at = datetime.fromisoformat(data.get("endedAt").replace("Z", "+00:00"))
            except Exception:
                pass
                
        cost = data.get("cost")
        
        # Extract transcript & turns from messages
        turns = []
        messages = data.get("messages", [])
        transcript = data.get("transcript") or ""
        
        speech_messages = [
            m for m in messages 
            if m.get("role") in ("assistant", "user", "bot", "customer") and m.get("message")
        ]
        
        for i, msg in enumerate(speech_messages):
            role = msg.get("role")
            speaker = "agent" if role in ("assistant", "bot") else "user"
            text = msg.get("message", "")
            
            start_sec = msg.get("secondsFromStart", 0.0)
            if start_sec is None:
                start_sec = 0.0
                
            estimated_duration = len(text) / 15.0 + 0.5
            
            if i < len(speech_messages) - 1:
                next_start = speech_messages[i+1].get("secondsFromStart")
                if next_start is not None:
                    end_sec = min(start_sec + estimated_duration, next_start)
                else:
                    end_sec = start_sec + estimated_duration
            else:
                end_sec = start_sec + estimated_duration
                
            if duration_sec > 0:
                end_sec = min(end_sec, duration_sec)
                
            turns.append({
                "speaker": speaker,
                "start_sec": round(float(start_sec), 2),
                "end_sec": round(float(max(end_sec, start_sec + 0.1)), 2),
                "text": text
            })
            
        tool_calls = self._extract_tool_calls(messages)
            
        return {
            "external_id": call_id,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "audio_url": audio_url,
            "duration_sec": duration_sec,
            "started_at": started_at,
            "ended_at": ended_at,
            "cost": cost,
            "transcript": transcript,
            "turns": turns,
            "tool_calls": tool_calls,
            "metadata": data
        }

    def fetch_call_data(self, call_id: str) -> Dict[str, Any]:
        return self.get_call(call_id)

    def list_calls(
        self,
        agent_id: Optional[str] = None,
        created_after: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieves call list for Vapi assistant with optional createdAtGt filter.
        """
        if self.api_key == "mock" or self.api_key.startswith("mock_"):
            return self._get_mock_calls_list(agent_id, created_after)

        url = "https://api.vapi.ai/call"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params: Dict[str, Any] = {"limit": min(limit, 100)}
        if agent_id:
            params["assistantId"] = agent_id
        if created_after:
            params["createdAtGt"] = created_after.isoformat()

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            raw_calls = data if isinstance(data, list) else data.get("calls", data.get("data", []))
            calls_list = []

            for item in raw_calls:
                call_id = item.get("id")
                st = None
                if item.get("createdAt"):
                    try:
                        st = datetime.fromisoformat(item["createdAt"].replace("Z", "+00:00"))
                    except Exception:
                        pass
                        
                et = None
                if item.get("endedAt"):
                    try:
                        et = datetime.fromisoformat(item["endedAt"].replace("Z", "+00:00"))
                    except Exception:
                        pass

                calls_list.append({
                    "external_id": call_id,
                    "agent_id": item.get("assistantId") or agent_id,
                    "started_at": st,
                    "ended_at": et,
                    "duration_sec": int(item.get("duration", 0)),
                    "status": item.get("status", "ended"),
                    "cost": item.get("cost"),
                    "raw_metadata": item
                })

            return calls_list

        except Exception as e:
            logger.exception("Failed to fetch calls from Vapi API")
            return []

    def _get_mock_calls_list(self, agent_id: Optional[str], created_after: Optional[datetime]) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        return [
            {
                "external_id": "mock_vapi_call_001",
                "agent_id": agent_id or "assistant_vapi_01",
                "started_at": now,
                "ended_at": now,
                "duration_sec": 45,
                "status": "ended",
                "cost": 0.0320,
                "raw_metadata": {"mocked": True, "id": "mock_vapi_call_001"}
            },
            {
                "external_id": "mock_vapi_call_002",
                "agent_id": agent_id or "assistant_vapi_02",
                "started_at": now,
                "ended_at": now,
                "duration_sec": 60,
                "status": "ended",
                "cost": 0.0480,
                "raw_metadata": {"mocked": True, "id": "mock_vapi_call_002"}
            }
        ]

    def _get_mock_data(self, call_id: str) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        messages = [
            {
                "role": "assistant",
                "message": "Hello, thank you for calling Benten Support. How can I help you today?",
                "secondsFromStart": 0.5
            },
            {
                "role": "user",
                "message": "Hi, I am setting up the provider ingestion task.",
                "secondsFromStart": 5.0
            },
            {
                "role": "tool-call",
                "toolCalls": [
                    {
                        "id": "call_mock_1",
                        "type": "function",
                        "function": {
                            "name": "check_deployment_status",
                            "arguments": "{\"project_id\": \"benten-prod\"}"
                        }
                    }
                ],
                "secondsFromStart": 12.0,
                "time": int(now.timestamp() * 1000) + 12000
            },
            {
                "role": "tool-call-result",
                "toolCallId": "call_mock_1",
                "name": "check_deployment_status",
                "result": "{\"status\": \"healthy\", \"uptime\": \"18d\", \"version\": \"2.4.1\"}",
                "secondsFromStart": 14.2,
                "time": int(now.timestamp() * 1000) + 14200
            }
        ]
        tool_calls = self._extract_tool_calls(messages)
        return {
            "external_id": call_id,
            "agent_id": "assistant_vapi_01",
            "agent_name": "Mock Vapi Assistant",
            "audio_url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
            "duration_sec": 45,
            "started_at": now,
            "ended_at": now,
            "cost": 0.0320,
            "transcript": "Agent: Hello, thank you for calling Benten Support.",
            "turns": [
                {
                    "speaker": "agent",
                    "start_sec": 0.5,
                    "end_sec": 4.2,
                    "text": "Hello, thank you for calling Benten Support. How can I help you today?"
                },
                {
                    "speaker": "user",
                    "start_sec": 5.0,
                    "end_sec": 10.5,
                    "text": "Hi, I am setting up the provider ingestion task."
                }
            ],
            "tool_calls": tool_calls,
            "metadata": {
                "id": call_id,
                "status": "ended",
                "mocked": True,
                "messages": messages
            }
        }

    def list_agents(self) -> List[Dict[str, Any]]:
        """
        Retrieves and normalizes assistants from Vapi.ai API.
        """
        if self.api_key == "mock" or self.api_key.startswith("mock_"):
            return [
                {
                    "external_id": "assistant_vapi_01",
                    "name": "Vapi Customer Support Voice Bot",
                    "description": "Voice assistant configured with GPT-4o and Deepgram Nova-2 STT",
                    "created_at": "2025-01-15T10:00:00Z",
                    "raw_metadata": {
                        "id": "assistant_vapi_01",
                        "name": "Vapi Customer Support Voice Bot",
                        "model": {"provider": "openai", "model": "gpt-4o"},
                        "transcriber": {"provider": "deepgram", "model": "nova-2"},
                        "firstMessage": "Hello, thank you for calling support."
                    }
                },
                {
                    "external_id": "assistant_vapi_02",
                    "name": "Vapi Outbound Appointment Scheduler",
                    "description": "Automated appointment booking assistant with Google Calendar action bindings",
                    "created_at": "2025-02-01T14:30:00Z",
                    "raw_metadata": {
                        "id": "assistant_vapi_02",
                        "name": "Vapi Outbound Appointment Scheduler",
                        "model": {"provider": "anthropic", "model": "claude-3-5-sonnet"},
                        "firstMessage": "Hi! I am calling to confirm your appointment."
                    }
                }
            ]

        url = "https://api.vapi.ai/assistant"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            agents_list = []
            if isinstance(data, list):
                raw_assistants = data
            elif isinstance(data, dict):
                raw_assistants = data.get("assistants", data.get("data", []))
            else:
                raw_assistants = []

            for ast in raw_assistants:
                model_info = ast.get("model", {})
                model_name = model_info.get("model") if isinstance(model_info, dict) else str(model_info)
                first_msg = ast.get("firstMessage", "")

                desc_parts = []
                if model_name:
                    desc_parts.append(f"Model: {model_name}")
                if first_msg:
                    desc_parts.append(f"Greeting: {first_msg[:60]}...")

                agents_list.append({
                    "external_id": ast.get("id"),
                    "name": ast.get("name") or f"Vapi Assistant ({ast.get('id', 'unknown')})",
                    "description": " | ".join(desc_parts) if desc_parts else None,
                    "created_at": ast.get("createdAt"),
                    "raw_metadata": ast
                })

            return agents_list

        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("Failed to fetch assistants from Vapi API")
            raise

