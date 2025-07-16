#!/bin/sh
set -e

# Load environment variables from /app/.env if present
if [ -f "/app/.env" ]; then
  echo "Loading environment variables from /app/.env"
  set -a
  . /app/.env
  set +a
fi

exec "$@"
