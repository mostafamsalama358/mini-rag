from celery import Celery

from helpers.config import get_settings

settings = get_settings()

_long_task_limit = settings.CELERY_LONG_TASK_TIME_LIMIT
_long_task_soft_limit = max(_long_task_limit - 120, int(_long_task_limit * 0.9))
_default_soft_limit = max(settings.CELERY_TASK_TIME_LIMIT - 60, 1)

celery_app = Celery(
    "algorag",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "tasks.file_processing",
        "tasks.data_indexing",
        "tasks.process_workflow",
        "tasks.maintenance",
        "tasks.knowledge_representation",
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
    task_soft_time_limit=_default_soft_limit,
    task_ignore_resul=False,
    result_expires=3600,
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    worker_max_tasks_per_child=100,
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    worker_cancel_long_running_tasks_on_connection_loss=True,
    task_routes={
        "tasks.file_processing.process_project_files": {"queue": "file_processing"},
        "tasks.data_indexing.index_data_content": {"queue": "data_indexing"},
        "tasks.data_indexing.index_data_content_shard": {"queue": "data_indexing"},
        "tasks.data_indexing.finalize_vector_index": {"queue": "data_indexing"},
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
    task_annotations={
        "tasks.file_processing.process_project_files": {
            "time_limit": _long_task_limit,
            "soft_time_limit": _long_task_soft_limit,
        },
        "tasks.data_indexing.index_data_content": {
            "time_limit": _long_task_limit,
            "soft_time_limit": _long_task_soft_limit,
        },
        "tasks.data_indexing.index_data_content_shard": {
            "time_limit": _long_task_limit,
            "soft_time_limit": _long_task_soft_limit,
        },
        "tasks.data_indexing.finalize_vector_index": {
            "time_limit": _long_task_limit,
            "soft_time_limit": _long_task_soft_limit,
        },
        "tasks.process_workflow.push_after_process_task": {
            "time_limit": _long_task_limit,
            "soft_time_limit": _long_task_soft_limit,
        },
    },
)

celery_app.conf.task_default_queue = "default"


from celery.signals import worker_ready


@worker_ready.connect
def _ingest_orphan_recovery_on_worker_ready(sender=None, **kwargs):
    """Best-effort orphan reclaim on worker boot (017)."""
    import asyncio
    import logging

    log = logging.getLogger(__name__)
    if not settings.INGEST_RELIABILITY_ENABLED:
        return

    async def _run() -> None:
        from celery_runtime import get_db_client
        from services.ingest_reliability.orphans import recover_stale_orphans

        engine = None
        try:
            engine, db_client = await get_db_client()
            outcomes = await recover_stale_orphans(db_client)
            if outcomes:
                log.info("ingest orphan recovery: %s", outcomes)
        except Exception as exc:
            log.warning("ingest orphan recovery skipped: %s", exc)
        finally:
            if engine is not None:
                await engine.dispose()

    try:
        asyncio.run(_run())
    except Exception as exc:
        log.warning("ingest orphan recovery bootstrap failed: %s", exc)
