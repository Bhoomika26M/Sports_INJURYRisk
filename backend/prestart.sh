#!/bin/sh
set -e

echo "=== [1/2] Applying database migrations with Alembic ==="
alembic upgrade head

echo "=== [2/2] Seeding initial admin user ==="
python -m app.scripts.seed_admin

echo "=== Pre-start steps complete. Starting server ==="
exec "$@"
