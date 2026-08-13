#!/data/data/com.termux/files/usr/bin/bash
set -e
RUN_ID="$1"
DEST="$2"

cat > "$DEST/MANIFEST.md" <<EOF
# Census Engine Run Manifest

Run ID: $RUN_ID
Generated: $(date -Iseconds)

## Local paths

- Raw: $DEST/raw
- Reports: $DEST/reports
- URLs: $DEST/urls.txt

## Key outputs

- $DEST/raw/guardian_manifest.jsonl
- $DEST/raw/guardian_summary.json
- $DEST/reports/evidence_report.md
- $DEST/reports/evidence_graph.json
- $DEST/reports/evidence_graph.graphml
- $DEST/reports/entity_resolution.json
- $DEST/reports/hash_chain.json

## Doctrine

CATTER chooses the seed.
Guardian preserves the source.
Ledger holds the witness.
Graph shows the body.
Review separates truth from noise.
EOF
