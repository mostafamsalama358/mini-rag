# Dockerfile

## What is this?

Instructions to **build the Docker image** for the Python app.

In .NET terms: like a `Dockerfile` that builds your API project.

## Why does it exist?

Docker needs to know:

1. Which Python version to use
2. Which packages to install
3. Which files to copy
4. How to start the app

## What it does (step by step)

1. Starts from Python 3.10 image with `uv` (fast pip)
2. Installs system tools (gcc, libxml, etc.)
3. Copies `src/requirements.txt` and installs packages
4. Copies all of `src/` into `/app`
5. Copies Alembic config and `entrypoint.sh`
6. Runs migrations on start, then starts Uvicorn on port 8000

## Where is it used?

| File | Link |
|------|------|
| `docker/docker-compose.yml` | `fastapi`, `celery-worker`, `celery-beat`, and `flower` all build from this Dockerfile |
| `docker/minirag/entrypoint.sh` | Runs before the main command |
| `docker/minirag/alembic.example.ini` | Becomes `alembic.ini` inside the container |

## Related source files

- `src/main.py` → started by Uvicorn
- `src/requirements.txt` → Python packages list
- `src/celery_app.py` → used by Celery containers
