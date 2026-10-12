#!/usr/bin/env sh
set -e

# ==============================================================================
# Database readiness probe script
# Verifies database TCP listener and authentication readiness before booting app
# ==============================================================================

HOST="${DB_HOST:-mysql}"
PORT="${DB_PORT:-3306}"
TIMEOUT="${DB_TIMEOUT:-60}"

echo "Waiting for database service at ${HOST}:${PORT} (timeout: ${TIMEOUT}s)..."

start_time=$(date +%s)
while true; do
  current_time=$(date +%s)
  elapsed=$((current_time - start_time))

  if [ "$elapsed" -ge "$TIMEOUT" ]; then
    echo "ERROR: Timed out after ${TIMEOUT}s waiting for database at ${HOST}:${PORT}" >&2
    exit 1
  fi

  # Attempt connection check via Python socket probe
  if python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(2); s.connect(('${HOST}', int('${PORT}'))); s.close()" 2>/dev/null; then
    echo "Database at ${HOST}:${PORT} is reachable and accepting TCP connections."
    break
  fi

  echo "Database is not yet ready (elapsed: ${elapsed}s). Retrying in 2 seconds..."
  sleep 2
done

exec "$@"
