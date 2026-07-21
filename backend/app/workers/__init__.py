from celery import Celery
from celery.signals import worker_process_init
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
    # ML workload tuning: each task is long-running and CPU-heavy
    worker_max_tasks_per_child=None,      # Never restart workers (preserves preloaded models)
    worker_prefetch_multiplier=1,         # Don't prefetch — tasks are long-running
    worker_concurrency=2,                 # Limit concurrent workers to reduce memory/CPU thrashing
)

# Automatically discover tasks in tasks.py and worker modules
celery_app.autodiscover_tasks(["app.workers"], force=True)


@worker_process_init.connect
def preload_models_on_worker_start(**kwargs):
    """
    Preload all ML models (VAD, Diarizer, Sentiment) when each worker
    process starts. This shifts the ~16s init cost from the first task
    to worker startup, so tasks execute immediately.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Worker process starting — preloading ML models...")
    try:
        from app.pipeline.scoring import preload_all_models
        preload_all_models()
    except Exception as e:
        logger.warning(f"Model preloading failed (tasks will lazy-load): {e}")

