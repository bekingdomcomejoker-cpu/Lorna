#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
DB=${DB:-census.sqlite}
URLS=${1:-urls.txt}
OUT=${2:-guardian_raw}
mkdir -p "$OUT" reports logs
python -m census_engine --db "$DB" guardian "$URLS" --out "$OUT" --depth ${DEPTH:-0} --max-pages ${MAX_PAGES:-50} --delay ${DELAY:-0.5} | tee logs/guardian_$(date +%Y%m%d_%H%M%S).json
