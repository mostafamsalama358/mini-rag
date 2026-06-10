# celery_task_execution.py

## What is this?

SQLAlchemy entity for table `celery_task_executions`.

Stores **history of Celery background tasks**.

## Why does it exist?

Supports idempotency: know if a task already ran, failed, or is stuck.

Also useful for debugging and audit.

## Main columns

| Column | Meaning |
|--------|---------|
| `task_name` | Celery task path |
| `task_args_hash` | SHA-256 of arguments |
| `celery_task_id` | Celery UUID |
| `status` | PENDING, STARTED, SUCCESS, FAILURE |
| `task_args` / `result` | JSON data |

## Where is it used?

| File | How |
|------|-----|
| `src/utils/idempotency_manager.py` | Create/update/query records |
| `src/tasks/file_processing.py` | Tracks process task |
| `src/tasks/maintenance.py` | Deletes old rows |
| Alembic migrations | Creates and updates this table |

## .NET comparison

Like a `BackgroundJobExecution` table for Hangfire job state.
