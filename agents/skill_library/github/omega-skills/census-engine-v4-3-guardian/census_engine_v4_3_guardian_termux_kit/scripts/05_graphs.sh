#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .venv/bin/activate ] && . .venv/bin/activate
mkdir -p reports
python -m census_engine graph --db census.sqlite --format json --out reports/evidence_graph.json
python -m census_engine graph --db census.sqlite --format graphml --out reports/evidence_graph.graphml
