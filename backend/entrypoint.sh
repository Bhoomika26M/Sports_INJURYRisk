#!/usr/bin/env bash
set -e

echo "=== AthletiQ Production Backend Startup ==="

# Wait for PostgreSQL database readiness if DB_HOST is set
if [ -n "$DB_HOST" ]; then
  echo "Waiting for database at $DB_HOST:${DB_PORT:-5432}..."
  python - << END
import socket
import time
import os
import sys

host = os.environ.get("DB_HOST", "localhost")
port = int(os.environ.get("DB_PORT", 5432))
timeout = 30
start = time.time()

while time.time() - start < timeout:
    try:
        with socket.create_connection((host, port), timeout=2):
            print(f"Connected to database at {host}:{port} successfully.")
            sys.exit(0)
    except (socket.error, socket.timeout):
        time.sleep(1)

print(f"Timed out waiting for database at {host}:{port}.")
sys.exit(0)
END
fi

# Run database schema migrations
echo "Running Alembic database migrations..."
alembic upgrade head || {
  echo "Alembic upgrade warning: proceeding with automatic runtime table generation."
}

# Optional demo seeding
if [ "$SEED_DEMO_DATA" = "true" ] || [ "$SEED_DEMO_DATA" = "1" ]; then
  echo "Seeding demo accounts and biomechanical trials..."
  python seed_demo.py || echo "Demo seed completed or skipped."
fi

# Start Uvicorn application server
WORKERS=${UVICORN_WORKERS:-4}
PORT=${PORT:-8000}
echo "Starting Uvicorn server with $WORKERS workers on port $PORT..."
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers "$WORKERS" --proxy-headers --forwarded-allow-ips "*"
