import os

from celery import Celery

celery_app = Celery(
    "tax_ai_advisor",
    broker=os.getenv("TAX_AI_CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("TAX_AI_CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
    include=["app.workers.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    task_publish_retry=False,
    broker_connection_timeout=2,
    worker_prefetch_multiplier=1,
    timezone="UTC",
    beat_schedule={
        "monitor-legal-sources-every-72-hours": {
            "task": "legal_sources.check_all",
            "schedule": 72 * 60 * 60,
        }
    },
)
