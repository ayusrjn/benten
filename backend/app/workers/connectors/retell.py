import requests
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.workers.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

class RetellConnector(BaseConnector):
    """
    Connector for Retell API.
    Retrieves call details, recording URL, word-level timestamps, and speaker turns.
    """
    def verify_key(self) -> tuple[bool, str]:
        if self.api_key == "mock" or self.api_key.startswith("mock_"):
            return True, "Mock Retell API key valid"
        try:
            url = "https://api.retellai.com/v3/list-calls"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            res = requests.post(url, headers=headers, json={"limit": 1}, timeout=10)
            if res.status_code == 200:
                return True, "Successfully connected to Retell API"
            elif res.status_code in (401, 403):
                return False, "Invalid Retell API key"
            return False, f"Retell API returned status code {res.status_code}"
        except Exception as e:
            return False, f"Failed to connect to Retell: {str(e)}"

    def _extract_tool_calls(self, data: Dict[str, Any], turns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        tool_calls_map = {}
        transcript_with_tool_calls = data.get("transcript_with_tool_calls") or []
        
        current_time_sec = 0.0
        turn_index = 0
        
        for item in transcript_with_tool_calls:
            role = item.get("role")
            if role in ("agent", "user"):
                if turn_index < len(turns):
                    t = turns[turn_index]
                    current_time_sec = t.get("end_sec", current_time_sec)
                    turn_index += 1
            elif role == "tool_call":
                tc_id = item.get("tool_call_id") or item.get("id")
                name = item.get("name") or item.get("function", {}).get("name")
                args = item.get("arguments") or item.get("function", {}).get("arguments")
                
                tool_calls_map[tc_id] = {
                    "id": tc_id,
                    "name": name,
                    "arguments": args,
                    "start_time_sec": current_time_sec,
                    "latency_ms": None,
                    "result": None,
                    "error": None
                }
            elif role == "tool_result":
                tc_id = item.get("tool_call_id") or item.get("id")
                content = item.get("content") or item.get("result")
                if tc_id in tool_calls_map:
                    tool_calls_map[tc_id]["result"] = content
        
        latency_info = data.get("latency") or {}
        if isinstance(latency_info, dict):
            tc_latencies = latency_info.get("tool_calls") or []
            if isinstance(tc_latencies, list):
                for idx, tcl in enumerate(tc_latencies):
                    if not isinstance(tcl, dict):
                        continue
                    name = tcl.get("name")
                    lat_sec = tcl.get("latency") or tcl.get("duration")
                    matched = False
                    if lat_sec is not None:
                        lat_ms = int(lat_sec * 1000) if lat_sec < 100 else int(lat_sec)
                        for tc in tool_calls_map.values():
                            if tc["name"] == name and tc["latency_ms"] is None:
                                tc["latency_ms"] = lat_ms
                                matched = True
                                break
                        if not matched:
                            new_id = f"tool_lat_{idx}"
                            tool_calls_map[new_id] = {
                                "id": new_id,
                                "name": name,
                                "arguments": None,
                                "start_time_sec": None,
                                "latency_ms": lat_ms,
                                "result": None,
                                "error": None
                            }
        
        result_list = list(tool_calls_map.values())
        result_list.sort(key=lambda x: x["start_time_sec"] or 0.0)
        return result_list

    def get_call(self, call_id: str) -> Dict[str, Any]:
        if self.api_key == "mock" or call_id.startswith("mock_"):
            return self._get_mock_data(call_id)

        url = f"https://api.retellai.com/v2/get-call/{call_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Duration
        duration_ms = data.get("duration_ms")
        if duration_ms is not None:
            duration_sec = int(duration_ms / 1000)
        else:
            duration_sec = int(data.get("duration_sec", data.get("duration", 0)))
            
        audio_url = data.get("recording_url") or data.get("audio_url")
        agent_name = data.get("agent_name") or data.get("agent_id") or "Retell Agent"
        agent_id = data.get("agent_id")
        
        # Timestamps and cost
        started_at = None
        if data.get("start_timestamp"):
            try:
                started_at = datetime.fromtimestamp(data["start_timestamp"] / 1000.0, tz=timezone.utc)
            except Exception:
                pass
                
        ended_at = None
        if data.get("end_timestamp"):
            try:
                ended_at = datetime.fromtimestamp(data["end_timestamp"] / 1000.0, tz=timezone.utc)
            except Exception:
                pass
                
        cost = None
        call_cost = data.get("call_cost")
        if isinstance(call_cost, (int, float)):
            cost = float(call_cost) / 100.0
        elif isinstance(call_cost, dict):
            combined = call_cost.get("combined_cost")
            if isinstance(combined, (int, float)):
                cost = float(combined) / 100.0
            else:
                product_costs = call_cost.get("product_costs") or []
                cost = sum(float(item.get("cost", 0.0)) for item in product_costs) / 100.0 if product_costs else 0.0
            
        transcript = data.get("transcript") or ""
        
        # Extract turns from transcript_object
        turns = []
        transcript_obj = data.get("transcript_object", [])
        
        for i, turn in enumerate(transcript_obj):
            role = turn.get("role") or turn.get("speaker")
            speaker = "agent" if role in ("agent", "assistant", "bot") else "user"
            text = turn.get("content") or turn.get("text", "")
            
            words = turn.get("words", [])
            if words:
                start_sec = words[0].get("start", 0.0)
                end_sec = words[-1].get("end", start_sec + 0.1)
            else:
                start_sec = 0.0
                if turns:
                    start_sec = turns[-1]["end_sec"] + 0.5
                estimated_duration = len(text) / 15.0 + 0.5
                end_sec = start_sec + estimated_duration
                
            if duration_sec > 0:
                end_sec = min(end_sec, duration_sec)
                
            turns.append({
                "speaker": speaker,
                "start_sec": round(float(start_sec), 2),
                "end_sec": round(float(max(end_sec, start_sec + 0.1)), 2),
                "text": text
            })
            
        tool_calls = self._extract_tool_calls(data, turns)
            
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
        Retrieves call list from Retell AI via POST /v3/list-calls.
        """
        if self.api_key == "mock" or self.api_key.startswith("mock_"):
            return self._get_mock_calls_list(agent_id, created_after)

        url = "https://api.retellai.com/v3/list-calls"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        body: Dict[str, Any] = {"limit": min(limit, 100)}
        if agent_id:
            body["filter_criteria"] = {"agent_id": [agent_id]}

        try:
            response = requests.post(url, headers=headers, json=body, timeout=10)
            response.raise_for_status()
            raw_calls = response.json()

            if not isinstance(raw_calls, list):
                raw_calls = raw_calls.get("calls", [])

            calls_list = []
            for call in raw_calls:
                cid = call.get("call_id")
                st = None
                if call.get("start_timestamp"):
                    st = datetime.fromtimestamp(call["start_timestamp"] / 1000.0, tz=timezone.utc)

                if call.get("end_timestamp"):
                    et = datetime.fromtimestamp(call["end_timestamp"] / 1000.0, tz=timezone.utc)

                dur_ms = call.get("duration_ms")
                dur = int(dur_ms / 1000) if dur_ms else int(call.get("duration", 0))

                cost_val = call.get("call_cost")
                if isinstance(cost_val, (int, float)):
                    cost = float(cost_val) / 100.0
                elif isinstance(cost_val, dict):
                    combined = cost_val.get("combined_cost")
                    if isinstance(combined, (int, float)):
                        cost = float(combined) / 100.0
                    else:
                        product_costs = cost_val.get("product_costs") or []
                        cost = sum(float(item.get("cost", 0.0)) for item in product_costs) / 100.0 if product_costs else 0.0
                else:
                    cost = None

                calls_list.append({
                    "external_id": cid,
                    "agent_id": call.get("agent_id") or agent_id,
                    "started_at": st,
                    "ended_at": et,
                    "duration_sec": dur,
                    "status": call.get("call_status", "completed"),
                    "cost": cost,
                    "raw_metadata": call
                })

            return calls_list

        except Exception as e:
            logger.exception("Failed to fetch calls from Retell API")
            return []

    def _get_mock_calls_list(self, agent_id: Optional[str], created_after: Optional[datetime]) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        return [
            {
                "external_id": "mock_retell_call_001",
                "agent_id": agent_id or "agent_retell_01",
                "started_at": now,
                "ended_at": now,
                "duration_sec": 60,
                "status": "completed",
                "cost": 0.0550,
                "raw_metadata": {"mocked": True, "call_id": "mock_retell_call_001"}
            },
            {
                "external_id": "mock_retell_call_002",
                "agent_id": agent_id or "agent_retell_02",
                "started_at": now,
                "ended_at": now,
                "duration_sec": 90,
                "status": "completed",
                "cost": 0.0820,
                "raw_metadata": {"mocked": True, "call_id": "mock_retell_call_002"}
            }
        ]

    def _get_mock_data(self, call_id: str) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        mock_meta = {
            "call_id": call_id,
            "status": "completed",
            "mocked": True,
            "transcript_with_tool_calls": [
                {
                    "role": "agent",
                    "content": "Hello! Thank you for calling Retell AI support center. My name is Alex. How can I assist you today?"
                },
                {
                    "role": "user",
                    "content": "Hello, I am testing the Retell connector integration."
                },
                {
                    "role": "tool_call",
                    "tool_call_id": "call_retell_mock_1",
                    "name": "lookup_user_account",
                    "arguments": "{\"user_email\": \"test@example.com\"}"
                },
                {
                    "role": "tool_result",
                    "tool_call_id": "call_retell_mock_1",
                    "name": "lookup_user_account",
                    "content": "{\"status\": \"premium\", \"account_id\": \"retell_987\"}"
                }
            ],
            "latency": {
                "tool_calls": [
                    {
                        "name": "lookup_user_account",
                        "latency": 1.450
                    }
                ]
            }
        }
        turns = [
            {
                "speaker": "agent",
                "start_sec": 1.0,
                "end_sec": 5.5,
                "text": "Hello! Thank you for calling Retell AI support center. My name is Alex. How can I assist you today?"
            },
            {
                "speaker": "user",
                "start_sec": 6.2,
                "end_sec": 12.0,
                "text": "Hello, I am testing the Retell connector integration."
            }
        ]
        tool_calls = self._extract_tool_calls(mock_meta, turns)
        return {
            "external_id": call_id,
            "agent_id": "agent_retell_01",
            "agent_name": "Mock Retell Agent",
            "audio_url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
            "duration_sec": 60,
            "started_at": now,
            "ended_at": now,
            "cost": 0.0550,
            "transcript": "Agent: Hello! Thank you for calling Retell AI support center.",
            "turns": turns,
            "tool_calls": tool_calls,
            "metadata": mock_meta
        }

    def list_agents(self) -> List[Dict[str, Any]]:
        """
        Retrieves and normalizes agents from Retell AI API.
        Tries direct agent listing endpoint first, falling back to call history derivation.
        """
        if self.api_key == "mock" or self.api_key.startswith("mock_"):
            return [
                {
                    "external_id": "agent_retell_01",
                    "name": "Retell Patient Triage & Intake Assistant",
                    "description": "HIPAA-compliant patient check-in and medical history collection agent",
                    "created_at": "2025-01-20T08:15:00Z",
                    "raw_metadata": {
                        "agent_id": "agent_retell_01",
                        "agent_name": "Retell Patient Triage & Intake Assistant",
                        "response_engine": {"type": "retell-llm"}
                    }
                },
                {
                    "external_id": "agent_retell_02",
                    "name": "Retell Billing & Claims Specialist",
                    "description": "Inbound revenue cycle and insurance verification specialist",
                    "created_at": "2025-02-10T11:45:00Z",
                    "raw_metadata": {
                        "agent_id": "agent_retell_02",
                        "agent_name": "Retell Billing & Claims Specialist",
                        "response_engine": {"type": "custom-llm"}
                    }
                }
            ]

        headers = {"Authorization": f"Bearer {self.api_key}"}

        # Option 1: Try direct list-agents endpoint
        try:
            url = "https://api.retellai.com/v2/list-agents"
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                agents_list = []
                items = data if isinstance(data, list) else data.get("agents", [])
                for item in items:
                    ag_id = item.get("agent_id") or item.get("id")
                    ag_name = item.get("agent_name") or item.get("name") or f"Retell Agent ({ag_id})"
                    agents_list.append({
                        "external_id": ag_id,
                        "name": ag_name,
                        "description": item.get("description") or f"Voice ID: {item.get('voice_id', 'default')}",
                        "created_at": item.get("last_modification_timestamp") or item.get("created_at"),
                        "raw_metadata": item
                    })
                if agents_list:
                    return agents_list
        except Exception:
            pass

        # Option 2 (Fallback): Derive agents from recent calls via POST /v3/list-calls
        try:
            url = "https://api.retellai.com/v3/list-calls"
            res = requests.post(url, headers=headers, json={"limit": 100}, timeout=10)
            res.raise_for_status()
            calls = res.json()

            unique_agents = {}
            for call in calls:
                ag_id = call.get("agent_id")
                if not ag_id:
                    continue

                if ag_id not in unique_agents:
                    ag_name = call.get("agent_name") or f"Retell Agent ({ag_id})"
                    unique_agents[ag_id] = {
                        "external_id": ag_id,
                        "name": ag_name,
                        "description": f"Derived from call history (Call ID: {call.get('call_id')})",
                        "created_at": None,
                        "raw_metadata": {
                            "agent_id": ag_id,
                            "agent_name": ag_name,
                            "sample_call_id": call.get("call_id")
                        }
                    }

            return list(unique_agents.values())

        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("Failed to fetch/derive agents from Retell API")
            raise

