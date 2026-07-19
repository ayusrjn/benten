import requests
from typing import Dict, Any, List
from app.workers.connectors.base import BaseConnector

class RetellConnector(BaseConnector):
    """
    Connector for Retell API.
    Retrieves call details, recording URL, and transcript speaker turns.
    """
    def fetch_call_data(self, call_id: str) -> Dict[str, Any]:
        if self.api_key == "mock" or call_id.startswith("mock_"):
            return self._get_mock_data(call_id)

        url = f"https://api.retellai.com/get-call/{call_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Extract duration
        duration_ms = data.get("duration_ms")
        if duration_ms is not None:
            duration_sec = int(duration_ms / 1000)
        else:
            duration_sec = int(data.get("duration_sec", data.get("duration", 0)))
            
        # Extract audio URL
        audio_url = data.get("recording_url") or data.get("audio_url")
        
        # Extract agent ID/name
        agent_name = data.get("agent_id") or "Retell Agent"
        
        # Extract turns from transcript_object
        turns = []
        transcript_obj = data.get("transcript_object", [])
        
        for i, turn in enumerate(transcript_obj):
            role = turn.get("role") or turn.get("speaker")
            speaker = "agent" if role in ("agent", "assistant", "bot") else "user"
            text = turn.get("content") or turn.get("text", "")
            
            # Extract start and end times from word list if available
            words = turn.get("words", [])
            if words:
                start_sec = words[0].get("start", 0.0)
                end_sec = words[-1].get("end", start_sec + 0.1)
            else:
                # Estimate timestamps if words are missing
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
            
        return {
            "audio_url": audio_url,
            "duration_sec": duration_sec,
            "agent_name": agent_name,
            "turns": turns,
            "metadata": data
        }

    def _get_mock_data(self, call_id: str) -> Dict[str, Any]:
        """
        Returns high-quality mock data for testing.
        """
        return {
            "audio_url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
            "duration_sec": 60,
            "agent_name": "Mock Retell Agent",
            "turns": [
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
                    "text": "Hello, I am testing the Retell connector integration. We need to verify that word level timestamps are parsed and speakers are mapped correctly."
                },
                {
                    "speaker": "agent",
                    "start_sec": 13.0,
                    "end_sec": 18.5,
                    "text": "Absolutely! The Retell connector reads from the transcript object array and parses the start and end of speech segments from the word-level objects."
                },
                {
                    "speaker": "user",
                    "start_sec": 19.5,
                    "end_sec": 21.0,
                    "text": "Perfect, that works for me."
                },
                {
                    "speaker": "agent",
                    "start_sec": 21.5,
                    "end_sec": 23.0,
                    "text": "Is there anything else I can help you with today?"
                },
                {
                    "speaker": "user",
                    "start_sec": 23.5,
                    "end_sec": 25.0,
                    "text": "No, that's all. Thank you."
                },
                {
                    "speaker": "agent",
                    "start_sec": 25.5,
                    "end_sec": 27.0,
                    "text": "Thank you for calling. Have a great day!"
                }
            ],
            "metadata": {
                "call_id": call_id,
                "status": "completed",
                "mocked": True
            }
        }
