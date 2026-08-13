#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .venv/bin/activate ] && . .venv/bin/activate
python -m census_engine verify-chain --db census.sqlite | tee reports/hash_chain_verification.json
