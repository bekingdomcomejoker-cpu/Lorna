#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python -m census_engine --db demo.sqlite init
python -m census_engine --db demo.sqlite ingest examples/sample_notes.txt
python -m census_engine --db demo.sqlite report --out reports/demo_report.md
python -m census_engine --db demo.sqlite graph --out reports/demo_graph.json
python -m census_engine --db demo.sqlite graph --format graphml --out reports/demo_graph.graphml
python -m census_engine --db demo.sqlite verify-chain
