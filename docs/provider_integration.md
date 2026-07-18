# Provider Integration Guide

This guide details the technical implementation of **Benten's Provider Connectors**. Connectors are asynchronous components triggered from the UI, running as Celery tasks to import calls, download audio, sync transcripts, and normalize metadata into Benten's schema.

---

## 1. Unified Connector Interface

All connectors must subclass the abstract `BaseConnector` interface. This ensures that provider-specific response structures are normalized into a standard output dictionary before database insertion and analysis pipeline activation.

### The Ingestion Base Class
```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseConnector(ABC):
    def __init__(self, api_key: str, config: Dict[str, Any]):
        self.api_key = api_key
        self.config = config

    @abstractmethod
    def fetch_metadata(self, provider_call_id: str) -> Dict[str, Any]:
        """
        Fetches metadata from the provider.
        Returns unified fields: duration_sec, agent_name, created_at, status.
        """
        pass

    @abstractmethod
    def download_audio_stream(self, provider_call_id: str) -> bytes:
        """
        Downloads the raw audio file binary from the provider.
        """
        pass

    @abstractmethod
    def fetch_transcript_segments(self, provider_call_id: str) -> list[Dict[str, Any]]:
        """
        Fetches the time-aligned transcript segments from the provider.
        Returns a list of segments with keys: speaker ('user' or 'agent'), start, end, text.
        """
        pass
```

---

## 2. Ingestion Lifecyle

1.  **UI Import Trigger:** User enters a `call_id` and hits "Import".
2.  **Celery Job Registry:** The API Gateway registers an `audio_ingest` task to RabbitMQ.
3.  **Authentication Fetch:** Celery loads the encrypted `api_key` and `config` from the `integrations` table.
4.  **Download & Archive:** 
    *   The connector class contacts the provider, fetches metadata, and downloads the audio binary.
    *   The audio is uploaded to MinIO: `s3://benten-recordings/{project_id}/{conversation_id}.wav`.
5.  **SQL Transaction:** Ingestion saves the base `conversations` metadata and schedules the `audio-analysis` Celery task.

---

## 3. Provider Configurations & API Definitions

### A. Vapi
*   **Authentication:** `Authorization: Bearer <vapi_api_key>`
*   **Endpoints:**
    *   Fetch call data: `GET https://api.vapi.ai/call/{id}`
*   **Response Handling:**
    *   **Audio URL:** Found in the JSON payload as `recordingUrl`.
    *   **Transcript segments:** Parsed from `transcript` or the detailed `messages` array:
        ```json
        {
          "messages": [
            {
              "role": "assistant",
              "message": "Hello! Welcome to VoiceCorp.",
              "time": 1721297700000,
              "endTime": 1721297704000
            }
          ]
        }
        ```

### B. Retell
*   **Authentication:** `Authorization: Bearer <retell_api_key>`
*   **Endpoints:**
    *   Fetch call data: `GET https://api.retellai.com/get-call/{call_id}`
*   **Response Handling:**
    *   **Audio URL:** Found in the JSON payload as `recording_url`.
    *   **Transcript segments:** Parsed from the time-aligned `transcript_object` structure:
        ```json
        [
          {
            "role": "agent",
            "content": "Hello! Welcome to VoiceCorp. How can I help you today?",
            "words": [
              { "word": "Hello!", "start": 0.0, "end": 0.8 },
              { "word": "Welcome", "start": 0.8, "end": 1.4 }
            ]
          }
        ]
        ```

### C. ElevenLabs
*   **Authentication:** `xi-api-key: <elevenlabs_api_key>`
*   **Endpoints:**
    *   Fetch conversation: `GET https://api.elevenlabs.io/v1/convai/conversations/{conversation_id}`
    *   Download audio: `GET https://api.elevenlabs.io/v1/convai/conversations/{conversation_id}/audio`
*   **Response Handling:**
    *   **Audio URL:** The audio is downloaded directly as a binary stream from the `/audio` endpoint.
    *   **Transcript segments:** Parsed from the `history` log:
        ```json
        {
          "history": [
            {
              "role": "agent",
              "message": "Hello, thank you for calling.",
              "time_in_call_secs": 0.2
            }
          ]
        }
        ```

### D. OpenAI Realtime API (Custom Proxy Ingestion)
OpenAI's Realtime API does not host persistent call history or recording URLs directly. Instead, calls run over client-to-server WebSockets/WebRTC.

*   **Benten Gateway Proxy:**
    To support OpenAI Realtime, Benten deploys an session proxy. This proxy intercepts raw WebRTC audio streams and records intermediate JSON events (`response.done`, `conversation.item.created`).
*   **Ingestion Endpoint:**
    *   Benten contacts the private Gateway DB or Local Directory: `GET https://gateway.voicecorp.com/sessions/{session_id}`
*   **Normalizer logic:**
    *   **Audio:** Pulls the stereo WAV file buffered on the gateway.
    *   **Transcript:** Maps the captured `response.done` event items into standard speaker turn segments.

---

## 4. Integration Settings Schema (`integrations.config`)

To configure connectors from the UI, credentials are saved as JSON fields in the database.

### Vapi
```json
{
  "provider": "vapi",
  "org_id": "vapi-org-12345",
  "api_endpoint": "https://api.vapi.ai"
}
```

### Retell
```json
{
  "provider": "retell",
  "api_endpoint": "https://api.retellai.com"
}
```

### ElevenLabs
```json
{
  "provider": "elevenlabs",
  "agent_id": "eleven-agent-abc"
}
```

### OpenAI Realtime
```json
{
  "provider": "openai",
  "gateway_url": "https://gateway.voicecorp.com",
  "webrtc_codec": "audio/PCM"
}
```
