# celery_app.py

## What is this?

Configures **Celery** — the background job system.

In .NET this is like **Hangfire** or **Azure Service Bus** workers.

## Why does it exist?

Some work is slow (read PDF, split text, save vectors).

The API should not block the user. Celery runs these jobs in the background.

## What it sets up

| Part | Purpose |
|------|---------|
| `celery_app` | Main Celery instance named `"minirag"` |
| Broker | RabbitMQ — where tasks are queued |
| Backend | Redis — where task results are stored |
| Queues | `default`, `file_processing`, `data_indexing` |
| Beat schedule | Cleans old task records every 10 seconds |

## Task modules it loads

These task modules under `src/tasks/`:

- `file_processing.py` — read files, save chunks
- `data_indexing.py` — push chunks to vector DB
- `process_workflow.py` — chain process + index
- `maintenance.py` — cleanup old task records

## Where is it used?

| File | How |
|------|-----|
| `docker/docker-compose.yml` | Celery worker, beat, and flower commands use `-A celery_app` |
| `src/.env.example` | `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` |
| `src/helpers/config.py` | Celery settings |
| `src/flowerconfig.py` | Flower dashboard config |
| Root `README.md` | Manual Celery run commands |

## Helper function

`get_setup_utils()` — builds DB, LLM, and vector DB clients for workers (same idea as `main.py` startup).
