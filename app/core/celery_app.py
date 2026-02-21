from celery import Celery, signals
from .config import settings
from app.core.logging import configure_logging
from app.core.metrics import TASK_SUCCESS, TASK_FAILURE, TASK_RETRY


celery_app = Celery(
    "luminalib",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.task_routes = {
    "app.workers.tasks.summarize_book": {"queue": "llm"},
    "app.workers.tasks.update_review_consensus": {"queue": "llm"},
    "app.workers.tasks.recompute_user_preferences": {"queue": "recs"},
    "app.workers.tasks.recompute_recommendations": {"queue": "recs"},
}

celery_app.autodiscover_tasks(["app.workers"])

# Ensure JSON logging for workers
configure_logging()


@signals.task_postrun.connect
def _task_postrun(sender=None, state=None, **kwargs):
    if state == "SUCCESS":
        TASK_SUCCESS.labels(task=sender.name if sender else "unknown").inc()


@signals.task_failure.connect
def _task_failure(sender=None, **kwargs):
    TASK_FAILURE.labels(task=sender.name if sender else "unknown").inc()


@signals.task_retry.connect
def _task_retry(sender=None, **kwargs):
    TASK_RETRY.labels(task=sender.name if sender else "unknown").inc()
