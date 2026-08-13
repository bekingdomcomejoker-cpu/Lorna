#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .venv/bin/activate ] && . .venv/bin/activate
./scripts/01_init.sh
./scripts/02_ingest_inbox.sh
./scripts/03_fetch_urls.sh
./scripts/04_report.sh
./scripts/05_graphs.sh
./scripts/06_resolve.sh
./scripts/07_verify_chain.sh
