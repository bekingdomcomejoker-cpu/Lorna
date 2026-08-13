#!/usr/bin/env bash
set -euo pipefail
python -m census_engine.cli manifest
python -m census_engine.cli report --out out/CENSUS_ENGINE_REPORT.md
echo "Report written to out/CENSUS_ENGINE_REPORT.md"
