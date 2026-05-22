#!/bin/bash
# Production start script — runs from backend/
# Starts the arq background worker as a daemon, then the API server in the
# foreground so Render (or any process supervisor) tracks the main process.
set -e

echo "==> Starting arq worker (background)"
arq app.worker.settings.WorkerSettings &

echo "==> Starting FastAPI server on port ${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
