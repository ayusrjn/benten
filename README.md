<div align="center">

<img src="./icon.png" alt="Benten Logo" width="120" style="border-radius: 20px; margin-bottom: 16px;" />

# Benten

### Voice AI Agents Audio Evaluation Platform

<p align="center">
  Benten is an audio evaluation and analytics platform built specifically for Voice AI agents. It connects directly to voice AI platforms to discover your agents, process call audio, and measure conversation quality, response latency, and speech dynamics.
</p>

---

</div>

## What is Benten

Unlike standard LLM evaluation tools that only analyze text transcripts, Benten evaluates the complete acoustic and conversational performance of human-to-agent voice calls.

When a customer speaks with a Voice AI agent, Benten measures key performance metrics:
- **Turn Latency**: The response delay from user speech input to agent voice output.
- **Dead Air Percentage**: Unintended silent pauses during the call session.
- **User Interruptions**: Occurrences where the user speaks over the agent.
- **Health Score**: A calculated quality score (0 to 100) combining speech metrics and conversation flow.

---

## Supported Integrations

Benten integrates directly with leading Voice AI providers. Adding an API key automatically discovers your agents, synchronizes metadata, and prepares them for call evaluation.

<table align="center" style="width: 100%;">
  <tr>
    <td align="center" width="33%">
      <img src="https://img.shields.io/badge/ElevenLabs-7E22CE?style=for-the-badge&logoColor=white" alt="ElevenLabs" style="border-radius: 6px; margin-bottom: 8px;" /><br />
      <strong>ElevenLabs Conversational AI</strong><br />
      <sub>Synchronizes agent metadata via Conversational AI APIs and monitors speech synthesis response times.</sub>
    </td>
    <td align="center" width="33%">
      <img src="https://img.shields.io/badge/Vapi_AI-0369A1?style=for-the-badge&logoColor=white" alt="Vapi AI" style="border-radius: 6px; margin-bottom: 8px;" /><br />
      <strong>Vapi AI</strong><br />
      <sub>Discovers Vapi assistants and monitors end-to-end turn latency and webhook execution delays.</sub>
    </td>
    <td align="center" width="33%">
      <img src="https://img.shields.io/badge/Retell_AI-047857?style=for-the-badge&logoColor=white" alt="Retell AI" style="border-radius: 6px; margin-bottom: 8px;" /><br />
      <strong>Retell AI</strong><br />
      <sub>Fetches agent profiles and call records, monitoring speech turn overlaps and silence ratios.</sub>
    </td>
  </tr>
</table>

---

## Key Features

- **Automated Agent Discovery**: Enter API keys in the dashboard to automatically sync agents across ElevenLabs, Vapi, and Retell.
- **Audio Analysis Pipeline**: Standardizes audio files, detects speech activity with Silero VAD, separates speaker turns with PyAnnote diarization, and measures latency, dead air, and interruptions.
- **Agents Dashboard**: View all discovered agents in a centralized interface with provider filtering, search, and metric cards.
- **Detailed Agent Drawer**: Inspect individual agent performance trends, health scores, and raw JSON metadata returned by provider APIs.
- **Incident Flaw Detection**: Dynamically flags performance issues such as latency spikes, high dead air percentage, and user barge-ins.
- **Authentication & Multi-Tenancy**: Complete JWT-based authentication system with user registration, login, and project-level data separation.

---

## System Architecture

Benten uses a modular microservices architecture:

- **Frontend (`frontend-benten`)**: React dashboard built with Refine framework, Ant Design components, and React Router.
- **Backend API (`backend`)**: FastAPI application providing user auth, integration key storage, agent management, and dashboard APIs.
- **Task Workers**: Celery workers powered by RabbitMQ for asynchronous audio processing and provider synchronization.
- **Caching and Messaging**: Redis for real-time pub/sub notifications and task cache.
- **Database**: PostgreSQL with Alembic database schema migrations.

---

## Project Structure

```
.
├── backend/                # FastAPI application, Celery workers, and audio pipeline
│   ├── app/                # Application source code
│   │   ├── api/            # API routers (auth, agents, integrations, dashboard)
│   │   ├── models/         # SQLAlchemy database models
│   │   ├── workers/        # Celery tasks and provider connectors
│   │   └── pipeline/       # Audio analysis and feature extraction engine
│   ├── migrations/         # Alembic database schema migrations
│   └── requirements.txt    # Python backend dependencies
├── frontend-benten/        # React + Refine dashboard UI
│   ├── src/                # Pages (Agents, Integrations, Dashboard, Auth)
│   └── package.json        # Frontend Node.js dependencies
├── docker/                 # PostgreSQL, Redis, and RabbitMQ Docker Compose setup
├── start_dev.sh            # One-command development server script
└── README.md               # Project documentation
```

---

## Getting Started

### 1. One-Command Setup

Run the orchestrator script to start all backing services, backend API, Celery worker, and frontend dashboard:

```bash
./start_dev.sh
```

Press `Ctrl+C` to stop all services simultaneously.

---

### 2. Manual Setup

#### Step 1: Start Backing Infrastructure
```bash
docker compose -f docker/docker-compose.yml up -d
```

#### Step 2: Start Backend Server and Celery Worker
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Run database migrations
alembic upgrade head

# Start FastAPI web server
uvicorn app.main:app --reload --port 8000

# Start Celery worker (in a separate terminal)
celery -A app.workers.celery_app worker --loglevel=info
```

#### Step 3: Start Frontend Dashboard
```bash
cd frontend-benten
npm install
npm run dev
```

---

## Application Endpoints

- **Frontend Dashboard**: http://localhost:5173
- **Backend API Docs (Swagger)**: http://localhost:8000/docs
- **RabbitMQ Management Console**: http://localhost:15672 (Username: `benten_mq`, Password: `mq_secure_pwd`)

---

## License

This project is licensed under the MIT License.