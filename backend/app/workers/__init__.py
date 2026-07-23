import logging
from celery import Celery
from celery.signals import worker_process_init
from app.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "benten_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # ML tuning: avoid worker restarts to keep preloaded models in memory
    worker_max_tasks_per_child=None,
    worker_prefetch_multiplier=1,
    worker_concurrency=2,
)

celery_app.autodiscover_tasks(["app.workers"], force=True)


@worker_process_init.connect
def preload_models_on_worker_start(**kwargs):
    """Preload ML models on worker process startup to offset initialization latency."""
    logger.info("Preloading ML models on worker startup...")
    try:
        from app.pipeline.scoring import preload_all_models
        preload_all_models()
    except Exception as e:
        logger.warning(f"Failed to preload models: {e}")
