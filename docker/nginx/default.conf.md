# default.conf

## What is this?

Nginx web server config.

Nginx sits in front of FastAPI and sends HTTP requests to it.

## Why does it exist?

- Users open **port 80** (normal web port)
- FastAPI runs on **port 8000** inside Docker
- Nginx forwards traffic: `localhost:80` → `fastapi:8000`

Also hides the metrics URL behind a secret path.

## Main rules

| URL path | Goes to |
|----------|---------|
| `/` | FastAPI at `http://fastapi:8000` |
| `/TrhBVe_m5gg2002_E5VVqS` | Prometheus metrics on FastAPI |

## Where is it used?

| File | How |
|------|-----|
| `docker/docker-compose.yml` | Mounted into the `nginx` container |
| `docker/prometheus/prometheus.yml` | Scrapes metrics from the secret path |
| `src/utils/metrics.py` | Sets up metrics endpoint |

## .NET comparison

Like IIS or YARP reverse proxy in front of your ASP.NET Core app.
