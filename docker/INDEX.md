# Mini-RAG — docker folder map

Simple guide for the **Docker** setup.

## What is `docker/`?

Everything needed to run the full stack in containers.

Like having `docker-compose.yml` + infra configs in a .NET microservices repo.

## Services (from docker-compose.yml)

| Service | Port | Job |
|---------|------|-----|
| fastapi | 8000 | Main API |
| nginx | 80 | Public web entry |
| pgvector | 5400 | PostgreSQL + vectors |
| qdrant | 6333 | Optional vector DB |
| rabbitmq | 5672, 15672 | Task queue |
| redis | 6379 | Task results |
| celery-worker | — | Background work |
| celery-beat | — | Scheduled tasks |
| flower | 5555 | Celery UI |
| prometheus | 9090 | Metrics |
| grafana | 3000 | Dashboards |

## Each config file has a `.md` doc

Example: open `docker-compose.yml.md` next to `docker-compose.yml`.

## Setup steps (short)

```bash
cd docker/env
cp .env.example.app .env.app
cp .env.example.postgres .env.postgres
# ... copy other examples ...

cd docker/minirag
cp alembic.example.ini alembic.ini

cd docker
docker compose up --build -d
```

## Skip this folder

| Path | Why |
|------|-----|
| `docker/mongodb/` | Old MongoDB **data files**, not source code — see `mongodb/README.md` |
| `docker/.env` | Your local secrets — never commit |

## Start here

1. `README.about.md` — full Docker README explained
2. `docker-compose.yml.md` — all services
3. `env/.env.example.app.md` — app settings
