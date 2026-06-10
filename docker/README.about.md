# README.md (docker folder)

## What is this?

Main documentation for the **Docker setup** of Mini-RAG.

The existing `README.md` explains how to start services, use volumes, and open Grafana.

## Why does it exist?

Docker has many services. This README is the starting point for:

- Copying env example files
- Running `docker compose up`
- Opening URLs (FastAPI, Grafana, Prometheus)
- Fixing connection errors

## Where is it used?

| File | How |
|------|-----|
| `docker/docker-compose.yml` | All services described here |
| Root `README.md` | Sends you to `cd docker` |
| `docker/minirag.service` | Production systemd uses same folder |
| Each `*.md` file next to config files | More detail per file |

## Quick map

```
docker/
├── docker-compose.yml    → starts everything
├── env/                  → secret env files (from examples)
├── minirag/              → app Docker image
├── nginx/                → reverse proxy
├── prometheus/           → metrics
└── rabbitmq/             → message broker config
```

## For .NET developers

Think of this folder as `docker-compose` + `launchSettings` + deployment docs in one place.
