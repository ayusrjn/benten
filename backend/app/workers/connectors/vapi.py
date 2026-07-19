import requests
from typing import Dict, Any, List
from app.workers.connectors.base import BaseConnector

class VapiConnector(BaseConnector):
    """
    Connector for Vapi.ai API.
    Retrieves call details, audio URL, and speaker message turns.
    """
    def fetch_call_data(self, call_id: str) -> Dict[str, Any]:
        if self.api_key == "mock" or call_id.startswith("mock_"):
            return self._get_mock_data(call_id)

        url = f"https://api.vapi.ai/call/{call_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Extract duration
        duration_sec = int(data.get("duration", 0))
        
        # Extract audio URL
        audio_url = data.get("recordingUrl")
        
        # Extract agent name
        assistant = data.get("assistant", {})
        agent_name = assistant.get("name") or data.get("assistantId") or "Vapi Agent"
        
        # Extract turns from messages
        turns = []
        messages = data.get("messages", [])
        
        # Filter for actual speaker turns
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
                
            # Estimate end time based on message length and next turn
            # Average reading speed is about 15 characters per second
            estimated_duration = len(text) / 15.0 + 0.5
            
            if i < len(speech_messages) - 1:
                next_start = speech_messages[i+1].get("secondsFromStart")
                if next_start is not None:
                    end_sec = min(start_sec + estimated_duration, next_start)
                else:
                    end_sec = start_sec + estimated_duration
            else:
                end_sec = start_sec + estimated_duration
                
            # Cap end_sec at duration if duration is available
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
            "audio_url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
            "duration_sec": 45,
            "agent_name": "Mock Vapi Assistant",
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
                    "text": "Hi, I am setting up the provider ingestion. The Celery tasks seem to be triggering correctly, but I need to make sure the database saves speech segments."
                },
                {
                    "speaker": "agent",
                    "start_sec": 11.2,
                    "end_sec": 16.8,
                    "text": "That's great. Yes, the database stores speech segments chunked by creation time in a hypertable. Let's make sure the turns are parsed properly."
                },
                {
                    "speaker": "user",
                    "start_sec": 17.5,
                    "end_sec": 20.0,
                    "text": "Excellent, everything looks good on my end. Thank you!"
                },
                {
                    "speaker": "agent",
                    "start_sec": 20.5,
                    "end_sec": 23.0,
                    "text": "You're welcome. Have a wonderful day!"
                }
            ],
            "metadata": {
                "id": call_id,
                "status": "ended",
                "mocked": True
            }
        }
