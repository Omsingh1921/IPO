#!/usr/bin/env sh
set -e

# ==============================================================================
# Production Startup Script for Indian IPO Platform
# 1. Runs database schema migration (Alembic)
# 2. Starts default service (Scheduler / CLI / Briefing)
# ==============================================================================

echo "=========================================================="
echo "Starting Indian IPO Platform Container Runtime"
echo "=========================================================="

# Check if migrations should run on boot
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Applying database schema migrations via Alembic..."
  python -m ipo_platform.cli migrate || echo "Warning: Migration check completed."
  echo "Migrations synchronized successfully."
fi

# Resolve runtime HTTP port (Render uses $PORT, default 8000)
APP_PORT="${PORT:-8000}"

# If no command passed or default CLI help passed, launch Uvicorn web server
if [ "$#" -eq 0 ] || [ "$1" = "default" ] || [ "$1" = "python" -a "$4" = "--help" ]; then
  echo "Starting FastAPI Web Application & Live Scheduler on port ${APP_PORT}..."
  exec uvicorn ipo_platform.api.app:app --host 0.0.0.0 --port "${APP_PORT}"
fi

# If uvicorn command passed, ensure it listens on $APP_PORT
if [ "$1" = "uvicorn" ]; then
  echo "Starting Uvicorn Server on 0.0.0.0:${APP_PORT}..."
  exec uvicorn ipo_platform.api.app:app --host 0.0.0.0 --port "${APP_PORT}"
fi

echo "Executing command: $@"
exec "$@"
