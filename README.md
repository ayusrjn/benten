<div align="center">

# 🎙️ Benten
### Voice AI Agents Audio Evaluation Framework

[![Status](https://img.shields.io/badge/status-active-success.svg)](#)
[![Tech Stack](https://img.shields.io/badge/stack-React%20%7C%20Refine%20%7C%20Celery%20%7C%20RabbitMQ-blue.svg)](#)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](#)

<!-- LOGO PLACEHOLDER: Replace src with your hosted logo when available -->
<img src="https://placehold.co/600x200/1890ff/ffffff?text=BENTEN+AUDIO+EVALUATION" alt="Benten Logo" width="500" style="margin: 20px 0; border-radius: 8px;" />

<p align="center">
  <strong>A premium, multi-tenant analytics dashboard and signal-processing pipeline designed to measure, analyze, and optimize voice AI agent conversation quality.</strong>
</p>

---

</div>

Benten is a specialized **Voice AI Agents Audio Evaluation Framework**. Unlike text-only LLM evaluation platforms, Benten processes the complete acoustic and conversational dynamics of human-to-agent phone calls and voice sessions. It acts as an observation deck, highlighting bottlenecks in pipeline latency (STT $\rightarrow$ LLM $\rightarrow$ TTS), speech clarity, turn overlap, and customer emotion.

##  Key Features

*    **Batch Connector Ingestion**: Imports call data from voice AI providers (Vapi, Retell, OpenAI Realtime, ElevenLabs) using an asynchronous queue (RabbitMQ + Celery), streaming/evaluating audio streams directly from the provider's hosting API without local persistence.
*    **Sequential Audio Pipeline**:
    1.  **Audio Loader**: Standardizes codecs, loudness levels, and sample rates.
    2.  **Voice Activity Detection (VAD)**: Pinpoints speech frames vs. silences.
    3.  **Speaker Diarization**: Clusters audio channels to segregate and attribute speech turns (User vs. Agent).
    4.  **Feature Extraction**: Calculates Prosody, Emotion timelines, Voice Quality (MOS), Speaking Rate (WPM), and Silence.
    5.  **Scoring Engine**: Evaluates overall conversation health (0-100) and catalogs issue flags.
*    **Evaluation Dashboard**: Built with React, Refine, and Ant Design, displaying high-level performance trends, interactive turn timelines, and emotional profiles.
*    **Alerting & Notification Engine**: Configurable thresholds to route warning and critical incidents to Slack, PagerDuty, or email.

---

##  System Design & Documentation

Detailed blueprints and architectural guides are available in the [docs/](file:///home/ayush-ranjan/Documents/benten/docs) directory:

*    **[Architecture Overview](file:///home/ayush-ranjan/Documents/benten/docs/architecture_overview.md)**: System topology, Celery analysis pipeline steps, and extraction parameters.
*    **[Database Schema Design](file:///home/ayush-ranjan/Documents/benten/docs/database_schema.md)**: SQL DDL definitions, indexing strategies, and ERD mapping the hierarchy (`Organization` $\rightarrow$ `Project` $\rightarrow$ `Conversation`).

---

##  Technology Stack

*   **Frontend**: React, [Refine Dev Framework](https://refine.dev/), Ant Design, React Router.
*   **Message Broker**: RabbitMQ.
*   **Task Queue**: Celery (Python-based worker pools).
*   **Cache & PubSub**: Redis.
*   **Database**: PostgreSQL + TimescaleDB (for relational metadata and time-series metrics partitioning).

---

##  Project Structure

```bash
├── docs/                # Technical design documents and plans
├── frontend/            # Refine-based React dashboard app
└── README.md            # Root repository guide
```

---

##  Getting Started (Frontend)

To run the dashboard development server locally:

```bash
cd frontend
npm install
npm run dev
```

The UI dev server will launch at `http://localhost:5173`.