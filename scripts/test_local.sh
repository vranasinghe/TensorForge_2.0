#!/bin/sh
set -eu
python -m pytest -q
python -m scripts.offline_smoke
