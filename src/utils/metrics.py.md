# metrics.py

## What is this?

Sets up **Prometheus metrics** for the FastAPI app.

Tracks how many requests you get and how fast they are.

## Why does it exist?

Production apps need monitoring.

Prometheus scrapes metrics from a secret URL. Grafana shows charts.

## What it adds

| Metric | Meaning |
|--------|---------|
| `http_requests_total` | Count of requests (by method, path, status) |
| `http_request_duration_seconds` | How long each request took |

## Main function

```python
setup_metrics(app)
```

- Adds middleware to every request
- Exposes GET `/TrhBVe_m5gg2002_E5VVqS` (hidden from Swagger)

## Where is it used?

| File | How |
|------|-----|
| `src/main.py` | `setup_metrics(app)` on startup |
| `docker/prometheus/prometheus.yml` | Scrapes the metrics path |
| `docker/nginx/default.conf` | Proxies metrics URL |
| `src/requirements.txt` | `prometheus-client`, `starlette-exporter` |

## .NET comparison

Like `app.UseHttpMetrics()` with prometheus-net in ASP.NET Core.
