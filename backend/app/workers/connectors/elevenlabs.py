import os
import requests
import logging
from typing import Dict, Any, List
from app.workers.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

class ElevenLabsConnector(BaseConnector):
    """
    Connector for ElevenLabs Conversational AI API.
    Retrieves session details, downloads the raw conversation audio, 
    and parses conversational turns.
    """
    def fetch_call_data(self, call_id: str) -> Dict[str, Any]:
        if self.api_key == "mock" or call_id.startswith("mock_"):
            return self._get_mock_data(call_id)

        # 1. Fetch conversation metadata and turns
        metadata_url = f"https://api.elevenlabs.io/v1/convai/conversations/{call_id}"
        headers = {"xi-api-key": self.api_key}
        
        response = requests.get(metadata_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Extract duration
        duration_sec = 0
        call_metadata = data.get("metadata", {})
        if call_metadata:
            duration_sec = int(call_metadata.get("duration_sec", 0))
            
        agent_name = data.get("agent_name") or data.get("agent_id") or "ElevenLabs Agent"
        
        # Extract turns
        turns = []
        raw_turns = data.get("turns", [])
        
        for turn in raw_turns:
            role = turn.get("role")
            speaker = "agent" if role in ("agent", "assistant") else "user"
            text = turn.get("message") or turn.get("text", "")
            
            start_sec = turn.get("start_time_sec", 0.0)
            end_sec = turn.get("end_time_sec", start_sec + 0.1)
            
            turns.append({
                "speaker": speaker,
                "start_sec": round(float(start_sec), 2),
                "end_sec": round(float(end_sec), 2),
                "text": text
            })
            
        if not duration_sec and turns:
            duration_sec = int(turns[-1]["end_sec"])

        # 2. Download the raw audio and save it locally
        audio_url = f"https://api.elevenlabs.io/v1/convai/conversations/{call_id}/audio"
        audio_local_path = ""
        try:
            # We save the file to backend/app/storage/audio/
            storage_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "audio"))
            os.makedirs(storage_dir, exist_ok=True)
            
            local_filename = f"{call_id}.wav"
            local_filepath = os.path.join(storage_dir, local_filename)
            
            logger.info(f"Downloading ElevenLabs audio for {call_id} to {local_filepath}")
            audio_response = requests.get(audio_url, headers=headers, timeout=30, stream=True)
            audio_response.raise_for_status()
            
            with open(local_filepath, "wb") as f:
                for chunk in audio_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        
            # Return relative path for static serving
            audio_local_path = f"/static/audio/{local_filename}"
            logger.info(f"Successfully saved ElevenLabs audio to {audio_local_path}")
        except Exception as e:
            logger.exception(f"Failed to download audio for ElevenLabs call {call_id}")
            # Fall back to using the API endpoint directly as the audio_url
            audio_local_path = audio_url

        return {
            "audio_url": audio_local_path,
            "duration_sec": duration_sec,
            "agent_name": agent_name,
            "turns": turns,
            "metadata": data
        }

    def _get_mock_data(self, call_id: str) -> Dict[str, Any]:
        """
        Returns high-quality mock data for testing.
        """
        # Save a mock empty file or just return a mock URL
        # For simplicity in mock mode, return a public URL
        return {
            "audio_url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
            "duration_sec": 50,
            "agent_name": "Mock ElevenLabs Agent",
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
                },
                {
                    "speaker": "user",
                    "start_sec": 16.0,
                    "end_sec": 18.2,
                    "text": "Excellent, that makes perfect sense."
                },
                {
                    "speaker": "agent",
                    "start_sec": 19.0,
                    "end_sec": 21.0,
                    "text": "Glad I could help. Let me know if you need anything else!"
                }
            ],
            "metadata": {
                "conversation_id": call_id,
                "status": "completed",
                "mocked": True
            }
        }
