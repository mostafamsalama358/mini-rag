from celery import Celery

from helpers.config import get_settings

settings = get_settings()

celery_app = Celery(
    "algorag",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "tasks.file_processing",
        "tasks.data_indexing",
        "tasks.process_workflow",
        "tasks.maintenance",
    ],
)

celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_TASK_SERIALIZER,
    accept_content=[
        settings.CELERY_TASK_SERIALIZER
    ],
    task_acks_late=settings.CELERY_TASK_ACKS_LATE,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_ignore_resul=False,
    result_expires=3600,
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    worker_max_tasks_per_child=1,
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    worker_cancel_long_running_tasks_on_connection_loss=True,
    task_routes={
        "tasks.file_processing.process_project_files": {"queue": "file_processing"},
        "tasks.data_indexing.index_data_content": {"queue": "data_indexing"},
        "tasks.process_workflow.process_and_push_workflow": {"queue": "file_processing"},
        "tasks.maintenance.clean_celery_executions_table": {"queue": "default"},
    },
    beat_schedule={
        "cleanup-old-task-records": {
            "task": "tasks.maintenance.clean_celery_executions_table",
            "schedule": settings.CELERY_TASK_CLEANUP_INTERVAL_SECONDS,
            "args": (),
        }
    },
    timezone="UTC",
)

celery_app.conf.task_default_queue = "default"
