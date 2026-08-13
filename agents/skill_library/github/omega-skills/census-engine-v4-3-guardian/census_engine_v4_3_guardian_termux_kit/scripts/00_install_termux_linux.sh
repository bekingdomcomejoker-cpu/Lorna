#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv || { echo "Install python3-venv first. Termux: pkg install python"; exit 1; }
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
mkdir -p evidence_inbox reports exports logs
python -m census_engine init --db census.sqlite
