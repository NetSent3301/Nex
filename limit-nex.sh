#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR/backend"

../.venv/bin/uvicorn api.routes:app --reload --host 0.0.0.0 --port 8765 &
PID=$!

# Throttle to ~80% CPU using STOP/CONT cycles
(
  while kill -0 "$PID" 2>/dev/null; do
    sleep 1.2
    kill -STOP "$PID" 2>/dev/null
    sleep 0.3
    kill -CONT "$PID" 2>/dev/null
  done
) &

echo "Nex iniciado (PID $PID) con límite ~80% CPU"
wait "$PID"
