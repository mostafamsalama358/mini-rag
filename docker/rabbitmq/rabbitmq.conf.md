# rabbitmq.conf

## What is this?

Extra settings for the **RabbitMQ** message broker.

RabbitMQ carries tasks from FastAPI to Celery workers.

## Why does it exist?

Default RabbitMQ settings are not always good for this project.

This file sets:

- Memory limit (60% of RAM)
- Minimum free disk space (2 GB)
- Management UI on port 15672
- Log level

## Where is it used?

| File | How |
|------|-----|
| `docker/docker-compose.yml` | Mounted into the `rabbitmq` container at `/etc/rabbitmq/rabbitmq.conf` |
| `docker/env/.env.example.rabbitmq` | User/password for RabbitMQ |
| `src/celery_app.py` | Connects to RabbitMQ via `CELERY_BROKER_URL` |
| `src/.env.example` | Example broker URL with RabbitMQ credentials |

## .NET comparison

Like configuring RabbitMQ or Azure Service Bus connection for background workers.
