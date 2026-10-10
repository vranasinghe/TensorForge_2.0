#!/bin/sh
# Single-worker API start for Docker, Render, and any host that sets PORT.
# Local `docker run -p 8000:8000` stays valid because PORT defaults to 8000.
set -eu
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
