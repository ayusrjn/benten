import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.api import auth, stream, integrations, projects, agents, conversations, alerts, organization, dashboard
from app.database import engine, Base
import app.models.user

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Create storage directory for audio files if it doesn't exist
storage_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "storage"))
os.makedirs(os.path.join(storage_dir, "audio"), exist_ok=True)
app.mount("/static", StaticFiles(directory=storage_dir), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["x-total-count"],
)

app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(stream.router, prefix=settings.API_V1_STR)
app.include_router(integrations.router, prefix=settings.API_V1_STR)
app.include_router(projects.router, prefix=settings.API_V1_STR)
app.include_router(agents.router, prefix=settings.API_V1_STR)
app.include_router(conversations.router, prefix=settings.API_V1_STR)
app.include_router(alerts.alerts_router, prefix=settings.API_V1_STR)
app.include_router(alerts.rules_router, prefix=settings.API_V1_STR)
app.include_router(organization.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": "0.1.0"
    }
