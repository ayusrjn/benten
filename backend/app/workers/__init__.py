from celery import Celery
from app.config import settings

# Initialize Celery app
celery_app = Celery(
    "benten_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Standard configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

# Automatically discover tasks in tasks.py and worker modules
# celery_app.autodiscover_tasks(["app.workers"])
