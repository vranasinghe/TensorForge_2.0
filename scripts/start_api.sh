#!/bin/sh
# Single-worker API start for Docker, Render, and any host that sets PORT.
# Local `docker run -p 8000:8000` stays valid because PORT defaults to 8000.
set -eu
# Free Render is 512 MB; the vote artifact will OOM unless we load baseline.
if [ -n "${RENDER:-}" ] && [ -z "${ARTIFACT_DIR:-}" ]; then
  ARTIFACT_DIR=/srv/artifacts/baseline
  export ARTIFACT_DIR
fi
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
