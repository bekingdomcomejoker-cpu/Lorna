#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
if [ -s requirements.txt ]; then python -m pip install -r requirements.txt; fi
mkdir -p evidence_inbox reports exports logs
python -m census_engine init --db census.sqlite
printf '\nInstalled. Drop files into evidence_inbox/ then run ./run_all.sh\n'
