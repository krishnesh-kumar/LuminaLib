from prometheus_client import Counter

TASK_SUCCESS = Counter("celery_task_success_total", "Successful Celery tasks", ["task"])
TASK_FAILURE = Counter("celery_task_failure_total", "Failed Celery tasks", ["task"])
TASK_RETRY = Counter("celery_task_retry_total", "Retried Celery tasks", ["task"])
