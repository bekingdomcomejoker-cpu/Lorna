#!/usr/bin/env bash
set -euo pipefail
python -m census_engine.cli review --bucket "${1:-canon_core}" --limit "${2:-25}"
