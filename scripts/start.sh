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
  python -m ipo_platform.cli migrate
  echo "Migrations synchronized successfully."
fi

# Execute default command or user-provided arguments
if [ "$#" -eq 0 ]; then
  echo "No command passed. Launching interactive CLI help display..."
  exec python -m ipo_platform.cli --help
else
  echo "Executing command: $@"
  exec "$@"
fi
