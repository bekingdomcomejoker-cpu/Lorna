#!/data/data/com.termux/files/usr/bin/bash
set -e

echo "CATTER → Guardian → Graph Sync"
echo

read -p "Run ID: " RUN_ID
read -p "Target URL: " TARGET_URL
read -p "Target label: " TARGET_LABEL
read -p "Depth [default 1]: " DEPTH
read -p "Max pages [default 25]: " MAX_PAGES
read -p "Destination folder [default guardian_runs/RUN_ID]: " DEST

DEPTH="${DEPTH:-1}"
MAX_PAGES="${MAX_PAGES:-25}"
DB="${DB:-census.sqlite}"
DEST="${DEST:-guardian_runs/$RUN_ID}"

mkdir -p "$DEST/raw" "$DEST/reports"

cat > "$DEST/urls.txt" <<EOF
$TARGET_URL | $TARGET_LABEL
EOF

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
echo "DONE."
echo "Local: $DEST"
echo "Manifest: $DEST/MANIFEST.md"
echo "Report: $DEST/reports/evidence_report.md"
