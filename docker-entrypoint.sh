#!/bin/sh
set -e

echo "Running Alembic migrations (E3)..."
alembic -c /app/alembic.ini upgrade head || echo "alembic upgrade skipped/failed (may be first deploy; create_all will handle)"

# E1/E7: el mismo image soporta web (uvicorn) o worker (celery)
# SERVICE_ROLE=web | worker | beat

case "${SERVICE_ROLE}" in
  worker)
    echo "Starting Celery worker (concurrency=1, FFmpeg isolation)..."
    exec celery -A app.core.celery_app worker \
      --loglevel=info \
      --concurrency=1 \
      --pool=solo
    ;;
  beat)
    echo "Starting Celery beat (scheduled publishes)..."
    exec celery -A app.core.celery_app beat \
      --loglevel=info \
      --scheduler celery.beat:Scheduler
    ;;
  *)
    echo "Starting uvicorn (web)..."
    exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --log-level info
    ;;
esac