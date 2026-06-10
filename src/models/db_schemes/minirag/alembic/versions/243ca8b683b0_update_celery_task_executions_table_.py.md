# 243ca8b683b0_update_celery_task_executions_table_.py

## What is this?

Alembic migration that **updates** the `celery_task_executions` table.

## Why does it exist?

After the first version of the task table, the schema needed changes (indexes or columns).

This is a follow-up migration in the chain.

## Revision chain

- **Revision ID:** `243ca8b683b0`
- **After:** `b9f9e870b09b`

## Where is it used?

| File | How |
|------|-----|
| Alembic upgrade chain | Run after previous migrations |
| `celery_task_execution.py` | Final table shape should match entity |

## Note

Always run `alembic upgrade head` to apply all migrations in order.

## .NET comparison

Second EF migration altering an existing table.
