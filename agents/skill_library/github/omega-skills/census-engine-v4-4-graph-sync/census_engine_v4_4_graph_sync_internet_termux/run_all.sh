#!/data/data/com.termux/files/usr/bin/bash
set -e

RUN_ID="${RUN_ID:-latest}"
DEPTH="${DEPTH:-1}"
MAX_PAGES="${MAX_PAGES:-25}"
DB="${DB:-census.sqlite}"
DEST="${DEST:-guardian_runs/$RUN_ID}"
URLS="${URLS:-urls.txt}"

mkdir -p "$DEST/raw" "$DEST/reports"

if [ ! -f "$URLS" ]; then
  cat > "$URLS" <<'EOF'
https://en.wikipedia.org/wiki/Madlanga_Commission | Madlanga Commission seed node
EOF
fi

cp "$URLS" "$DEST/urls.txt"

./ce.sh --db "$DB" init

./ce.sh --db "$DB" guardian "$DEST/urls.txt" \
  --run-id "$RUN_ID" \
  --out "$DEST/raw" \
  --depth "$DEPTH" \
  --max-pages "$MAX_PAGES"

./ce.sh --db "$DB" sync-graph \
  --run "$RUN_ID" \
  --raw "$DEST/raw" \
  --reports "$DEST/reports"

./ce.sh --db "$DB" report --run "$RUN_ID" --out "$DEST/reports/evidence_report.md"
./ce.sh --db "$DB" graph --run "$RUN_ID" --format json --out "$DEST/reports/evidence_graph.json"
./ce.sh --db "$DB" graph --run "$RUN_ID" --format graphml --out "$DEST/reports/evidence_graph.graphml"
./ce.sh --db "$DB" resolve --out "$DEST/reports/entity_resolution.json"
./ce.sh --db "$DB" verify-chain --out "$DEST/reports/hash_chain.json"

./scripts/write_run_manifest.sh "$RUN_ID" "$DEST"

echo
echo "DONE"
echo "Run folder: $DEST"
echo "Report: $DEST/reports/evidence_report.md"
echo "Graph JSON: $DEST/reports/evidence_graph.json"
echo "GraphML: $DEST/reports/evidence_graph.graphml"
