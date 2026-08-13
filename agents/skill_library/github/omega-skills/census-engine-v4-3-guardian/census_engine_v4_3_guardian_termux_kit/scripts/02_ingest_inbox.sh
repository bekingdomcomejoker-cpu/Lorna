#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .venv/bin/activate ] && . .venv/bin/activate
mkdir -p evidence_inbox logs
python -m census_engine ingest evidence_inbox --db census.sqlite | tee logs/ingest_$(date +%Y%m%d_%H%M%S).json
