# prometheus.yml

## What is this?

Config file for **Prometheus** (metrics collector).

Prometheus reads numbers from your apps every 15 seconds.

## Why does it exist?

You need to watch:

- FastAPI request count and speed
- Server CPU and disk (node-exporter)
- PostgreSQL health (postgres-exporter)
- Qdrant vector DB metrics

## What it scrapes

| Job name | Target | Path |
|----------|--------|------|
| fastapi | `fastapi:8000` | `/TrhBVe_m5gg2002_E5VVqS` |
| node-exporter | `node-exporter:9100` | default |
| prometheus | itself | default |
| qdrant | `qdrant:6333` | `/metrics` |
| postgres | `postgres-exporter:9187` | default |

## Where is it used?

| File | How |
|------|-----|
| `docker/docker-compose.yml` | Mounted into the `prometheus` container |
| `docker/nginx/default.conf` | Exposes the FastAPI metrics path |
| `docker/README.md` | Links to Grafana dashboards |
| `src/main.py` | Calls `setup_metrics(app)` on startup |

## .NET comparison

Like `prometheus-net` scrape config or OpenTelemetry exporter settings.
