#!/usr/bin/env bash
# Quick local dev start (no Docker required — uses local Postgres)
# Usage: bash scripts/dev_start.sh
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="$ROOT/synthetic-data"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

# ── 1. generate synthetic data if not present ─────────────────────────────
if [ ! -f "$DATA_DIR/api_gateway_traces.csv" ]; then
  echo ">>> Generating synthetic data…"
  python3 "$ROOT/scripts/generate_synthetic_data.py"
fi

# ── 2. install backend deps ───────────────────────────────────────────────
echo ">>> Installing backend deps…"
pip3 install -q -r "$BACKEND/requirements.txt"

# ── 3. start backend ─────────────────────────────────────────────────────
echo ">>> Starting backend on :8001…"
cd "$BACKEND"
DATABASE_URL="${DATABASE_URL:-postgresql://tokenflow:tokenflow@localhost:5432/tokenflow_db}" \
SYNTHETIC_DATA_DIR="$DATA_DIR" \
ALLOWED_ORIGINS="http://localhost:3000,http://localhost:3001" \
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload &
BACKEND_PID=$!

sleep 4

# ── 4. seed database on first run ─────────────────────────────────────────
echo ">>> Syncing all connectors…"
curl -s -X POST http://localhost:8001/api/integrations/sync/all/run > /dev/null && echo "    Sync complete"
curl -s -X POST http://localhost:8001/api/recommendations/generate  > /dev/null && echo "    Recommendations generated"

# ── 5. start frontend ─────────────────────────────────────────────────────
echo ">>> Starting frontend on :3001…"
cd "$FRONTEND"
NEXT_PUBLIC_API_URL=http://localhost:8001 npm run dev -- --port 3001 &
FRONTEND_PID=$!

echo ""
echo "┌─────────────────────────────────────────────┐"
echo "│  TokenFlow AI is running                    │"
echo "│  Frontend : http://localhost:3001           │"
echo "│  Backend  : http://localhost:8001           │"
echo "│  API docs : http://localhost:8001/docs      │"
echo "└─────────────────────────────────────────────┘"
echo ""
echo "Press Ctrl+C to stop all services."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" EXIT
wait
