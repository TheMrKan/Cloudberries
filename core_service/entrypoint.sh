#!/bin/sh
set -e

echo "[entrypoint] waiting for postgres..."
python wait_for_db.py

echo "[entrypoint] seeding data..."
python seed_all.py

echo "[entrypoint] starting uvicorn..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
