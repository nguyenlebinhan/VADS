from celery import Celery

from app.config.settings import get_settings

settings = get_settings()

celery_app = Celery(
    "vads",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.service.processing_tasks"],
)

celery_app.conf.update(
    accept_content=["json"],
    beat_schedule={
        "redispatch-uploaded-document-jobs": {
            "task": "vads.processing.redispatch_uploaded_jobs",
            "schedule": 60.0,
        }
    },
    broker_connection_retry_on_startup=True,
    enable_utc=True,
    result_serializer="json",
    task_always_eager=settings.celery_task_always_eager,
    task_acks_late=True,
    task_default_queue=settings.document_processing_queue,
    task_ignore_result=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "vads.processing.*": {"queue": settings.document_processing_queue},
    },
    task_serializer="json",
    timezone="UTC",
)
