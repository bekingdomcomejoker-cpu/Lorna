#!/data/data/com.termux/files/usr/bin/bash
set -e

DB="selftest.sqlite"
RUN_ID="selftest"
DEST="guardian_runs/$RUN_ID"

rm -f "$DB"
rm -rf "$DEST"
mkdir -p "$DEST/raw" "$DEST/reports" _selftest_site

cat > _selftest_site/index.html <<'HTML'
<html><head><title>Selftest Source</title></head>
<body>
<h1>Madlanga Commission Selftest</h1>
<p>On 24 March 2026 SAPS officers were arrested in Gauteng. Atlantis Motors Pty Ltd is a test organization line.</p>
<a href="page2.html">Second page</a>
</body></html>
HTML

cat > _selftest_site/page2.html <<'HTML'
<html><head><title>Second Source</title></head>
<body><p>Vusimuzi Matlala and Johannesburg appear in this public test page on 2026-06-07.</p></body></html>
HTML

cd _selftest_site
python -m http.server 8765 >/tmp/census_selftest_http.log 2>&1 &
PID=$!
cd ..

sleep 1

cat > "$DEST/urls.txt" <<'EOF'
http://127.0.0.1:8765/index.html | local selftest
EOF

./ce.sh --db "$DB" init
./ce.sh --db "$DB" guardian "$DEST/urls.txt" --run-id "$RUN_ID" --out "$DEST/raw" --depth 1 --max-pages 5
./ce.sh --db "$DB" sync-graph --run "$RUN_ID" --raw "$DEST/raw" --reports "$DEST/reports"
./ce.sh --db "$DB" report --run "$RUN_ID" --out "$DEST/reports/evidence_report.md"
./ce.sh --db "$DB" graph --run "$RUN_ID" --format json --out "$DEST/reports/evidence_graph.json"
./ce.sh --db "$DB" graph --run "$RUN_ID" --format graphml --out "$DEST/reports/evidence_graph.graphml"
./ce.sh --db "$DB" verify-chain --out "$DEST/reports/hash_chain.json"

kill "$PID" || true

echo "SELFTEST COMPLETE"
echo "Report: $DEST/reports/evidence_report.md"
echo "Graph: $DEST/reports/evidence_graph.json"
