# docker-compose.yml

## What is this?

This file starts all services for the Mini-RAG app with Docker.

It is like a **docker-compose** or **docker run** setup in .NET, but for many apps at once.

## Why does it exist?

The app needs many parts to work:

- FastAPI (the main API)
- PostgreSQL with pgvector (database)
- RabbitMQ + Redis + Celery (background jobs)
- Nginx (web front door)
- Prometheus + Grafana (monitoring)

This file connects them together.

## Where is it used?

| Used by | How |
|---------|-----|
| `docker/README.md` | Explains how to run `docker compose up` |
| Root `README.md` | Points you to `cd docker` then start services |
| `docker/minirag.service` | Linux service runs `docker compose up` from this folder |
| All Docker containers | Each `service:` block becomes one container |

## Main services inside

- **fastapi** → uses `docker/minirag/Dockerfile`
- **celery-worker / celery-beat / flower** → same image, different commands
- **nginx** → uses `docker/nginx/default.conf`
- **pgvector, qdrant, rabbitmq, redis** → databases and message queue
- **prometheus, grafana, node-exporter, postgres-exporter** → metrics

## Env files it reads

- `docker/env/.env.app` → app settings (copy from `.env.example.app`)
- `docker/env/.env.postgres` → PostgreSQL
- `docker/env/.env.grafana` → Grafana login
- `docker/env/.env.rabbitmq` → RabbitMQ
- `docker/env/.env.redis` → Redis password
- `docker/env/.env.postgres-exporter` → DB metrics
