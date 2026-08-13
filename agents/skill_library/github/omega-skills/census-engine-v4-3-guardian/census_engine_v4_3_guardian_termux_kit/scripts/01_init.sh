#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .venv/bin/activate ] && . .venv/bin/activate
python -m census_engine init --db census.sqlite
