#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
python -m census_engine.cli init
python -m census_engine.cli extract --input examples --out /tmp/census_history_events.jsonl
python -m census_engine.cli guardian --input examples --out /tmp/census_guardian_events.jsonl
python -m census_engine.cli status
python -m census_engine.cli report --out /tmp/CENSUS_REPORT.md
echo "[✓] selftest passed"
