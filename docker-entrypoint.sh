#!/bin/sh
set -e

# Docker containers should use environment variables passed via docker run -e
# or Docker secrets, not .env files. The .env file is intended for local development only.

exec "$@"
