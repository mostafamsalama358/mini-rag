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

## nginx service (lines 83–95)

### What does it do?

Nginx is the **front door** for HTTP traffic. It listens on **port 80** and forwards requests to FastAPI on `fastapi:8000` inside the Docker network. See `docker/nginx/default.conf.md` for routing details.

### Why keep it?

| Benefit | Explanation |
|---------|-------------|
| Standard web port | Users open `http://localhost` (port 80) instead of `http://localhost:8000` |
| Reverse proxy | Hides FastAPI’s internal port and hostname from clients |
| Request headers | Sets `X-Real-IP`, `X-Forwarded-For`, and `X-Forwarded-Proto` so the app sees the real client |
| Metrics path | Proxies the secret metrics URL (`/TrhBVe_m5gg2522_esvVqS`) used by Prometheus |
| Production pattern | Same layout as real deployments: proxy in front of the app (like IIS/YARP in .NET) |
| Room to grow | Later you can add SSL, static files, rate limits, or multiple backends without changing FastAPI |

### What if we remove it?

The stack **still runs** — FastAPI already exposes `8000:8000`, so the API stays reachable at `http://localhost:8000`.

What you **lose**:

- **Port 80 stops working** — `http://localhost` no longer reaches the app; every client must use `:8000`
- **No reverse proxy layer** — nothing sits in front of FastAPI for headers, routing, or future TLS
- **Prometheus scrape path** — if anything expects metrics via nginx on port 80, that path must be updated to hit FastAPI directly
- **Less production-like** — in production you usually want a proxy; removing nginx means dev and prod diverge more

**Summary:** nginx is optional for local development if you are fine with port 8000, but it is the intended public HTTP entry point for the compose stack.

## Env files it reads

- `docker/env/.env.app` → app settings (copy from `.env.example.app`)
- `docker/env/.env.postgres` → PostgreSQL
- `docker/env/.env.grafana` → Grafana login
- `docker/env/.env.rabbitmq` → RabbitMQ
- `docker/env/.env.redis` → Redis password
- `docker/env/.env.postgres-exporter` → DB metrics
