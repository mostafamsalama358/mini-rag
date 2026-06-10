# idempotency_manager.py

## What is this?

Helper to **avoid duplicate Celery tasks** and track task status in PostgreSQL.

**Idempotency** = running the same task twice does not break data.

## Why does it exist?

Celery can retry or receive duplicate messages.

This class:

1. Hashes task name + arguments
2. Saves record in `celery_task_executions` table
3. Skips work if the same task already succeeded
4. Cleans old records

## Main methods

| Method | Purpose |
|--------|---------|
| `should_execute_task()` | Run or skip? |
| `create_task_record()` | New DB row |
| `update_task_status()` | PENDING → STARTED → SUCCESS/FAILURE |
| `cleanup_old_tasks()` | Delete old rows |

## Where is it used?

| File | How |
|------|-----|
| `src/tasks/file_processing.py` | Wraps process task |
| `src/tasks/maintenance.py` | Calls `cleanup_old_tasks(5)` |
| `src/models/db_schemes/minirag/schemes/celery_task_execution.py` | SQLAlchemy model |
| `src/celery_app.py` | Beat schedule runs cleanup task |

## .NET comparison

Like storing Hangfire job id + args hash to prevent duplicate background runs.
