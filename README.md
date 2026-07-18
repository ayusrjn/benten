<div align="center">

# 🎙️ Benten
### Voice AI Agents Audio Evaluation Framework

[![Status](https://img.shields.io/badge/status-active-success.svg)](#)
[![Tech Stack](https://img.shields.io/badge/stack-React%20%7C%20Refine%20%7C%20Celery%20%7C%20RabbitMQ-blue.svg)](#)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](#)

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

##  Project Structure

```bash
├── docker/              # Docker Compose and Postgres initialization configurations
│   ├── docker-compose.yml
│   └── postgres-init/
├── backend/             # Python FastAPI, Celery worker, and ML evaluation pipeline
│   ├── app/             # Application source code
│   │   ├── main.py      # FastAPI web application entrypoint
│   │   ├── config.py    # Environment configuration & validation
│   │   ├── database.py  # SQLAlchemy session setup
│   │   ├── api/         # REST API routers
│   │   ├── models/      # Database models
│   │   ├── workers/     # Celery tasks and connectors
│   │   └── pipeline/    # Audio analysis pipeline stubs
│   ├── requirements.txt # Python dependency file
│   └── Dockerfile       # Container build setup for Web/Workers
├── frontend/            # Refine-based React dashboard app
├── start_dev.sh         # Local dev environment orchestrator
└── README.md            # Root repository guide
```

---

##  Getting Started

### ⚡ Quick Start (Orchestrated Startup)
The fastest way to spin up the local development environment (Docker backing services, backend virtual environment, npm package installations, FastAPI server, Celery worker, and frontend dashboard) is to run the orchestration script in the root directory:

```bash
./start_dev.sh
```
*Press `Ctrl+C` in that terminal to gracefully stop all running servers simultaneously.*

### 🛠️ Manual Component Startup

#### 1. Spin up Backing Infrastructure
Start the database, message broker, and caching servers using Docker Compose:
```bash
docker compose -f docker/docker-compose.yml up -d
```

#### 2. Start the Backend API & Workers
Initialize the Python virtual environment and run the server + worker:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env

# Run FastAPI app (with auto-reload)
uvicorn app.main:app --reload --port 8000

# Run Celery worker (in a separate terminal)
celery -A app.workers.celery_app worker --loglevel=info
```

#### 3. Start the Frontend Dashboard
Install Node dependencies and launch the Vite-based development server:
```bash
cd frontend
npm install
npm run dev
```

* The Frontend dashboard will launch at `http://localhost:5173`.
* The FastAPI backend API docs will be accessible at `http://localhost:8000/docs`.
* The RabbitMQ Management Console will be at `http://localhost:15672` (User: `benten_mq`, Pass: `mq_secure_pwd`).