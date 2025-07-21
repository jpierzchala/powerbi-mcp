#!/bin/sh
set -e

# Docker containers should receive environment variables via docker run -e 
# or Docker secrets, not from .env files. .env files are for local development only.

exec "$@"
