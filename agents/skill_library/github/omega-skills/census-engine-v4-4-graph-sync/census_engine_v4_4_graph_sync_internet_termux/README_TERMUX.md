# Census Engine v4.4 — Graph Sync + Internet Guardian Termux Kit

This is the working code version of the graph-sync packet.

## Main commands

```bash
./ce.sh --db census.sqlite init

./ce.sh --db census.sqlite guardian urls.txt \
  --run-id madlanga_001 \
  --out guardian_runs/madlanga_001/raw \
  --depth 1 \
  --max-pages 25

./ce.sh --db census.sqlite sync-graph \
  --run madlanga_001 \
  --raw guardian_runs/madlanga_001/raw \
  --reports guardian_runs/madlanga_001/reports

./ce.sh --db census.sqlite report --run madlanga_001 --out guardian_runs/madlanga_001/reports/evidence_report.md
./ce.sh --db census.sqlite graph --run madlanga_001 --format json --out guardian_runs/madlanga_001/reports/evidence_graph.json
./ce.sh --db census.sqlite graph --run madlanga_001 --format graphml --out guardian_runs/madlanga_001/reports/evidence_graph.graphml
./ce.sh --db census.sqlite resolve --out guardian_runs/madlanga_001/reports/entity_resolution.json
./ce.sh --db census.sqlite verify-chain --out guardian_runs/madlanga_001/reports/hash_chain.json
```

## Termux install

```bash
termux-setup-storage
pkg update -y
pkg install python unzip -y
cd ~/storage/downloads
unzip CENSUS_ENGINE_V4_4_GRAPH_SYNC_INTERNET_TERMUX_2026-06-07.zip
cd census_engine_v4_4_graph_sync_internet_termux
chmod +x ce.sh catter.sh run_all.sh install.sh scripts/*.sh
./install.sh
```

## One-shot internet run

```bash
cat > urls.txt <<'EOF'
https://en.wikipedia.org/wiki/Madlanga_Commission | Madlanga Commission seed node
EOF

RUN_ID=madlanga_001 DEPTH=1 MAX_PAGES=25 ./run_all.sh
```

## Interactive phone run

```bash
./catter.sh
```

## Output

```text
guardian_runs/<RUN_ID>/
  urls.txt
  MANIFEST.md
  raw/
    html/*.html
    text/*.txt
    meta/*.json
    guardian_manifest.jsonl
    guardian_summary.json
  reports/
    evidence_report.md
    evidence_graph.json
    evidence_graph.graphml
    entity_resolution.json
    hash_chain.json
```

## Core line

CATTER chooses the seed.
Guardian preserves the source.
Ledger holds the witness.
Graph shows the body.
Review separates truth from noise.
