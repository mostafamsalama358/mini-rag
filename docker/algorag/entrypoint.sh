#!/bin/bash
set -e

# Flower monitors Celery only — no database migrations needed.
if [[ "$*" == *"flower"* ]]; then
  exec "$@"
fi

echo "Running database migrations..."
cd /app/models/db_schemes/algorag/
alembic upgrade head
cd /app

exec "$@"
