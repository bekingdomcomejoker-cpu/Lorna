#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .venv/bin/activate ] && . .venv/bin/activate
mkdir -p reports
python -m census_engine report --db census.sqlite --out reports/evidence_report.md
