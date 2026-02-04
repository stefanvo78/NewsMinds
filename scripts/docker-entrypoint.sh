#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting API server..."
# Use gunicorn with multiple uvicorn workers so CPU-heavy background tasks
# (embedding generation, feed parsing) don't block HTTP request handling.
# Each worker is a separate process with its own GIL.
exec gunicorn src.api.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers "${GUNICORN_WORKERS:-2}" \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --graceful-timeout 30
