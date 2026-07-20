import os
import requests
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.workers.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

class ElevenLabsConnector(BaseConnector):
    """
    Connector for ElevenLabs Conversational AI API.
    Retrieves agent metadata, conversation call summaries, detailed turns,
    and downloads conversation audio.
    """
    def verify_key(self) -> tuple[bool, str]:
        if self.api_key == "mock" or self.api_key.startswith("mock_"):
            return True, "Mock ElevenLabs API key valid"
        try:
            url = "https://api.elevenlabs.io/v1/convai/agents"
            headers = {"xi-api-key": self.api_key}
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                return True, "Successfully connected to ElevenLabs API"
            elif res.status_code in (401, 403):
                return False, "Invalid ElevenLabs API key"
            return False, f"ElevenLabs API returned status code {res.status_code}"
        except Exception as e:
            return False, f"Failed to connect to ElevenLabs: {str(e)}"

    def get_call(self, call_id: str) -> Dict[str, Any]:
        if self.api_key == "mock" or call_id.startswith("mock_"):
            return self._get_mock_data(call_id)

        # 1. Fetch conversation metadata and turns
        metadata_url = f"https://api.elevenlabs.io/v1/convai/conversations/{call_id}"
        headers = {"xi-api-key": self.api_key}
        
        response = requests.get(metadata_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        call_metadata = data.get("metadata", {})
        duration_sec = int(data.get("call_duration_secs") or (call_metadata.get("duration_sec") if call_metadata else 0) or 0)
        agent_name = data.get("agent_name") or data.get("agent_id") or "ElevenLabs Agent"
        agent_id = data.get("agent_id")
        
        # Parse start/end timestamps
        started_at = None
        start_secs = data.get("start_time_unix_secs") or (call_metadata.get("start_time_unix_secs") if call_metadata else None)
        if start_secs:
            started_at = datetime.fromtimestamp(start_secs, tz=timezone.utc)
            
        ended_at = None
        if started_at and duration_sec:
            ended_at = datetime.fromtimestamp(start_secs + duration_sec, tz=timezone.utc)
            
        cost = data.get("cost") or (call_metadata.get("cost") if call_metadata else None)
        
        # Extract turns (ElevenLabs can return turns under 'transcript', 'messages', 'turns', or 'analysis.transcript')
        turns = []
        raw_turns = (
            data.get("transcript") or 
            data.get("messages") or 
            data.get("turns") or 
            (data.get("analysis", {}).get("transcript") if isinstance(data.get("analysis"), dict) else []) or 
            []
        )
        
        transcript_parts = []
        
        for turn in raw_turns:
            if not isinstance(turn, dict):
                continue
            role = turn.get("role") or turn.get("speaker") or "agent"
            speaker = "agent" if role in ("agent", "assistant", "bot") else "user"
            text = turn.get("message") or turn.get("text") or turn.get("content") or ""
            if text:
                transcript_parts.append(f"{speaker.capitalize()}: {text}")
            
            start_sec = turn.get("time_in_call_secs") or turn.get("start_time_sec") or turn.get("timestamp") or turn.get("start") or 0.0
            end_sec = turn.get("end_time_sec") or turn.get("end") or (float(start_sec) + max(0.5, len(text) / 15.0))
            
            turns.append({
                "speaker": speaker,
                "start_sec": round(float(start_sec), 2),
                "end_sec": round(float(end_sec), 2),
                "text": text
            })
            
        if not duration_sec and turns:
            duration_sec = int(turns[-1]["end_sec"])
            
        transcript = "\n".join(transcript_parts)

        # 2. Download raw audio recording if available
        audio_url_endpoint = f"https://api.elevenlabs.io/v1/convai/conversations/{call_id}/audio"
        audio_local_path = None
        try:
            storage_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "audio"))
            os.makedirs(storage_dir, exist_ok=True)
            
            local_filename = f"elevenlabs_{call_id}.mp3"
            local_filepath = os.path.join(storage_dir, local_filename)
            
            audio_response = requests.get(audio_url_endpoint, headers=headers, timeout=30, stream=True)
            if audio_response.status_code == 200:
                with open(local_filepath, "wb") as f:
                    for chunk in audio_response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                audio_local_path = f"/static/audio/{local_filename}"
                logger.info(f"Downloaded ElevenLabs audio recording for conversation {call_id} to {audio_local_path}")
            else:
                logger.info(f"ElevenLabs audio recording endpoint returned status {audio_response.status_code} for call {call_id}. Recording marked as unavailable.")
                audio_local_path = None
        except Exception as e:
            logger.warning(f"Failed to download audio for ElevenLabs call {call_id}: {e}")
            audio_local_path = None

        return {
            "external_id": call_id,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "audio_url": audio_local_path,
            "duration_sec": duration_sec,
            "started_at": started_at,
            "ended_at": ended_at,
            "cost": cost,
            "transcript": transcript,
            "turns": turns,
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
        Retrieves call list for ElevenLabs account/agent with cursor-based pagination.
        """
        if self.api_key == "mock" or self.api_key.startswith("mock_"):
            return self._get_mock_calls_list(agent_id, created_after)

        calls_list = []
        url = "https://api.elevenlabs.io/v1/convai/conversations"
        headers = {"xi-api-key": self.api_key}
        cursor = None

        while len(calls_list) < limit:
            params = {"page_size": min(100, limit - len(calls_list))}
            if agent_id:
                params["agent_id"] = agent_id
            if cursor:
                params["cursor"] = cursor

            try:
                response = requests.get(url, headers=headers, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                if isinstance(data, list):
                    raw_convs = data
                elif isinstance(data, dict):
                    raw_convs = (
                        data.get("conversations") or 
                        data.get("history") or 
                        data.get("data") or 
                        []
                    )
                else:
                    raw_convs = []

                for conv in raw_convs:
                    if not isinstance(conv, dict):
                        continue

                    cid = (
                        conv.get("conversation_id") or 
                        conv.get("id") or 
                        conv.get("call_id") or 
                        conv.get("external_id")
                    )
                    if not cid:
                        continue

                    start_secs = (
                        conv.get("start_time_unix_secs") or 
                        conv.get("created_at_unix_secs") or 
                        conv.get("start_time_sec") or 
                        conv.get("start_time") or 
                        conv.get("created_at")
                    )

                    conv_started_at = None
                    if isinstance(start_secs, (int, float)):
                        conv_started_at = datetime.fromtimestamp(start_secs, tz=timezone.utc)
                    elif isinstance(start_secs, str):
                        try:
                            conv_started_at = datetime.fromisoformat(start_secs.replace("Z", "+00:00"))
                        except Exception:
                            conv_started_at = None

                    duration = int(
                        conv.get("call_duration_secs") or 
                        conv.get("duration_sec") or 
                        conv.get("duration") or 
                        0
                    )

                    conv_ended_at = None
                    if conv_started_at and duration:
                        try:
                            conv_ended_at = datetime.fromtimestamp(
                                conv_started_at.timestamp() + duration, tz=timezone.utc
                            )
                        except Exception:
                            pass

                    calls_list.append({
                        "external_id": cid,
                        "agent_id": conv.get("agent_id") or agent_id,
                        "started_at": conv_started_at,
                        "ended_at": conv_ended_at,
                        "duration_sec": duration,
                        "status": conv.get("status", "completed"),
                        "cost": conv.get("cost"),
                        "raw_metadata": conv
                    })

                has_more = data.get("has_more", False) if isinstance(data, dict) else False
                next_cursor = data.get("next_cursor") if isinstance(data, dict) else None
                if not has_more or not next_cursor:
                    break
                cursor = next_cursor

            except Exception as e:
                logger.exception(f"Failed to fetch conversations list from ElevenLabs API: {e}")
                break

        return calls_list

    def _get_mock_calls_list(self, agent_id: Optional[str], created_after: Optional[datetime]) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        return [
            {
                "external_id": "mock_el_call_001",
                "agent_id": agent_id or "agent_el_01",
                "started_at": now,
                "ended_at": now,
                "duration_sec": 50,
                "status": "completed",
                "cost": 0.0450,
                "raw_metadata": {"mocked": True, "call_id": "mock_el_call_001"}
            },
            {
                "external_id": "mock_el_call_002",
                "agent_id": agent_id or "agent_el_02",
                "started_at": now,
                "ended_at": now,
                "duration_sec": 75,
                "status": "completed",
                "cost": 0.0620,
                "raw_metadata": {"mocked": True, "call_id": "mock_el_call_002"}
            }
        ]

    def _get_mock_data(self, call_id: str) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        return {
            "external_id": call_id,
            "agent_id": "agent_el_01",
            "agent_name": "Mock ElevenLabs Agent",
            "audio_url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
            "duration_sec": 50,
            "started_at": now,
            "ended_at": now,
            "cost": 0.0450,
            "transcript": "Agent: Welcome to ElevenLabs Voice Agent.\nUser: Testing audio ingestion.",
            "turns": [
                {
                    "speaker": "agent",
                    "start_sec": 0.0,
                    "end_sec": 3.5,
                    "text": "Welcome to ElevenLabs Voice Agent. How can I help you today?"
                },
                {
                    "speaker": "user",
                    "start_sec": 4.5,
                    "end_sec": 9.2,
                    "text": "Hi, I am testing the ElevenLabs audio ingestion task. Does it download the audio file correctly?"
                },
                {
                    "speaker": "agent",
                    "start_sec": 10.0,
                    "end_sec": 15.4,
                    "text": "Yes, it downloads the raw audio via the conversation audio API endpoint, saves it locally, and exposes it over the static path."
                }
            ],
            "metadata": {
                "conversation_id": call_id,
                "status": "completed",
                "mocked": True
            }
        }

    def list_agents(self) -> List[Dict[str, Any]]:
        if self.api_key == "mock" or self.api_key.startswith("mock_"):
            return [
                {
                    "external_id": "agent_el_01",
                    "name": "ElevenLabs Enterprise Sales Representative",
                    "description": "Conversational sales agent tuned for inbound enterprise inquiries",
                    "created_at": None,
                    "raw_metadata": {
                        "agent_id": "agent_el_01",
                        "name": "ElevenLabs Enterprise Sales Representative",
                        "tags": ["sales", "inbound", "enterprise"],
                        "archived": False
                    }
                },
                {
                    "external_id": "agent_el_02",
                    "name": "ElevenLabs Customer Support Concierge",
                    "description": "Tier 1 customer support agent with live tool integration",
                    "created_at": None,
                    "raw_metadata": {
                        "agent_id": "agent_el_02",
                        "name": "ElevenLabs Customer Support Concierge",
                        "tags": ["support", "tier1"],
                        "archived": False
                    }
                }
            ]

        agents_list = []
        url = "https://api.elevenlabs.io/v1/convai/agents"
        headers = {"xi-api-key": self.api_key}
        cursor = None

        while True:
            params = {"page_size": 100}
            if cursor:
                params["cursor"] = cursor

            try:
                response = requests.get(url, headers=headers, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                raw_agents = data.get("agents", [])
                for item in raw_agents:
                    agents_list.append({
                        "external_id": item.get("agent_id"),
                        "name": item.get("name") or "Unnamed ElevenLabs Agent",
                        "description": ", ".join(item.get("tags", [])) if item.get("tags") else None,
                        "created_at": item.get("created_at_unix_secs"),
                        "raw_metadata": item
                    })

                has_more = data.get("has_more", False)
                next_cursor = data.get("next_cursor")

                if not has_more or not next_cursor:
                    break
                cursor = next_cursor

            except Exception as e:
                logger.exception("Failed to fetch agents from ElevenLabs API")
                raise

        return agents_list


