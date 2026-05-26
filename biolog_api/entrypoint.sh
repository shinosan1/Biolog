#!/bin/sh
set -e

echo "[entrypoint] running migrations..."
python migrations/runner.py
echo "[entrypoint] migrations complete, starting API..."

exec uvicorn api:app --host 0.0.0.0 --port 8766
