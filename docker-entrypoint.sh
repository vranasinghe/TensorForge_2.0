#!/bin/sh
# Start as root only to fix ownership of the (possibly root-owned) job DB directory,
# then drop to the unprivileged user for the API process.
set -eu
DB_DIR="$(dirname "${JOB_DB:-/srv/runtime/jobs.sqlite3}")"
mkdir -p "$DB_DIR"
chown -R tensorforge:tensorforge "$DB_DIR"
exec setpriv --reuid=tensorforge --regid=tensorforge --init-groups "$@"
