# flowerconfig.py

## What is this?

Settings for **Flower** — a web UI to watch Celery workers and tasks.

## Why does it exist?

When jobs run in the background, you need a dashboard to see:

- Which tasks are running
- Which tasks failed
- Worker status

Flower gives you that at http://localhost:5555

## Main settings

| Setting | Value | Meaning |
|---------|-------|---------|
| `port` | 5555 | Web UI port |
| `max_tasks` | 10000 | Max tasks shown |
| `auto_refresh` | True | Page updates automatically |
| `basic_auth` | admin + password | Login protection |

Password comes from `CELERY_FLOWER_PASSWORD` in `.env`.

## Where is it used?

| File | How |
|------|-----|
| `docker/docker-compose.yml` | Flower container: `--conf=flowerconfig.py` |
| `src/.env.example` | `CELERY_FLOWER_PASSWORD` |
| `src/celery_app.py` | Same Celery app Flower monitors |
| Root `README.md` | Flower URL and run command |

## .NET comparison

Like Hangfire Dashboard or Azure Portal view for your job queue.
