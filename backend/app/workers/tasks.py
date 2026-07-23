import logging
from app.workers import celery_app
from app.database import SessionLocal
from app.workers.ingestion import process_call_ingestion, sync_calls_for_integration
from app.workers.evaluation import process_audio_evaluation
from app.workers.connectors import CONNECTORS

logger = logging.getLogger(__name__)

# Re-exports for backwards compatibility
__all__ = [
    "ingest_call",
    "sync_calls_task",
    "evaluate_audio",
    "sync_calls_for_integration",
    "CONNECTORS"
]


@celery_app.task(
    name="ingest_call",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=30
)
def ingest_call(self, project_id: str, provider: str, provider_call_id: str) -> str:
    db = SessionLocal()
    try:
        conversation_id, audio_url = process_call_ingestion(db, project_id, provider, provider_call_id)
        evaluate_audio.delay(conversation_id, audio_url)
        return conversation_id
    except Exception:
        logger.exception(f"Ingestion task failed for project: {project_id}, call: {provider_call_id}")
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(
    name="sync_calls",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=30
)
def sync_calls_task(self, project_id: str, provider: str) -> dict:
    db = SessionLocal()
    try:
        return sync_calls_for_integration(db, project_id, provider)
    except Exception:
        logger.exception(f"Sync task failed for project: {project_id}, provider: {provider}")
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(
    name="evaluate_audio",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=30
)
def evaluate_audio(self, conversation_id: str, audio_url: str) -> bool:
    try:
        return process_audio_evaluation(conversation_id, audio_url)
    except Exception:
        logger.exception(f"Audio evaluation task failed for: {conversation_id}")
        raise
