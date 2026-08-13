#!/usr/bin/env bash
set -euo pipefail
uvicorn census_engine.api:app --host 0.0.0.0 --port 8080
