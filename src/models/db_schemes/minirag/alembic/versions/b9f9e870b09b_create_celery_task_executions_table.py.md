# b9f9e870b09b_create_celery_task_executions_table.py

## What is this?

Alembic migration that adds **`celery_task_executions`** table.

## Why does it exist?

Background tasks need idempotency tracking in the database.

This migration creates the table used by `IdempotencyManager`.

## Revision chain

- **Revision ID:** `b9f9e870b09b`
- **After:** `fee4cd54bd38` (initial commit)

## Where is it used?

| File | How |
|------|-----|
| `src/models/db_schemes/minirag/schemes/celery_task_execution.py` | Entity definition |
| `src/utils/idempotency_manager.py` | Reads/writes this table |
| `src/tasks/file_processing.py` | Creates task records |

## .NET comparison

Migration adding `BackgroundJobExecutions` table.
