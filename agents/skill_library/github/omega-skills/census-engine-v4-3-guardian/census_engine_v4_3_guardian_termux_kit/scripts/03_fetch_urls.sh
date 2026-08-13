#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .venv/bin/activate ] && . .venv/bin/activate
python -m census_engine fetch-list urls.txt --db census.sqlite | tee logs/fetch_urls_$(date +%Y%m%d_%H%M%S).json
