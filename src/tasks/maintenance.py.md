# maintenance.py

## What is this?

**Celery maintenance task** that deletes old task execution records.

Task name: `tasks.maintenance.clean_celery_executions_table`

## Why does it exist?

`IdempotencyManager` saves every Celery run in PostgreSQL.

Without cleanup, the table grows forever.

## What it does

Runs `idempotency_manager.cleanup_old_tasks(5)` — deletes records older than 5 seconds (demo setting).

In production you would use a larger value (for example 86400 = 24 hours).

## Where is it used?

| File | How |
|------|-----|
| `src/celery_app.py` | Beat schedule every 10 seconds |
| `src/utils/idempotency_manager.py` | Does the actual delete |
| `docker/docker-compose.yml` | `celery-beat` container runs scheduler |

## .NET comparison

Like a scheduled cleanup job for old Hangfire or audit log rows.
