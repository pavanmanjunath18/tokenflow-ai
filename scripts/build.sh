#!/bin/bash
# Render build script — runs from the repo root (tokenflow_ai/)
set -e

echo "==> Python version"
python3 --version

echo "==> Installing Python dependencies"
pip install --upgrade pip
pip install -r backend/requirements.txt

echo "==> Generating synthetic data"
python3 scripts/generate_synthetic_data.py

echo "==> Applying database migrations"
cd backend && python -m alembic upgrade head

echo "==> Build complete"
