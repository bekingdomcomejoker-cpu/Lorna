#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
DB=${DB:-census.sqlite}
mkdir -p evidence_inbox reports logs guardian_raw exports
python -m census_engine --db "$DB" init
python -m census_engine --db "$DB" ingest evidence_inbox | tee logs/ingest_$(date +%Y%m%d_%H%M%S).json
if [ -f urls.txt ]; then
  python -m census_engine --db "$DB" guardian urls.txt --out guardian_raw --depth ${DEPTH:-0} --max-pages ${MAX_PAGES:-50} --delay ${DELAY:-0.5} | tee logs/guardian_$(date +%Y%m%d_%H%M%S).json
fi
python -m census_engine --db "$DB" report --out reports/evidence_report.md
python -m census_engine --db "$DB" graph --format json --out reports/evidence_graph.json
python -m census_engine --db "$DB" graph --format graphml --out reports/evidence_graph.graphml
python -m census_engine --db "$DB" resolve > reports/entity_resolution_candidates.json
python -m census_engine --db "$DB" verify-chain > reports/hash_chain_verification.json
printf '
DONE. Open reports/evidence_report.md and guardian_raw/guardian_summary.json
'
