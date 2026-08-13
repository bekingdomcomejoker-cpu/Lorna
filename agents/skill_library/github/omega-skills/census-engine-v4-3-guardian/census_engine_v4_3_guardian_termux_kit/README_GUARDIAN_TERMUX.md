# Census Engine v4.3 — Guardian Termux Layer

This package restores the Guardian layer as a real terminal command.

## Install on Termux

```bash
termux-setup-storage
cd ~/storage/downloads
unzip CENSUS_ENGINE_V4_3_GUARDIAN_TERMUX_KIT_2026-06-07.zip
cd census_engine_v4_3_guardian_termux_kit
chmod +x install.sh run_all.sh ce.sh scripts/*.sh
./install.sh
```

## Put URLs in `urls.txt`

Format:

```text
https://example.com/public-page | optional label
https://another-site.org/report
```

## Run Guardian only

```bash
./ce.sh --db census.sqlite guardian urls.txt --out guardian_raw
```

## Crawl same-domain links one level deep

```bash
DEPTH=1 MAX_PAGES=25 ./run_all.sh
```

Or directly:

```bash
./ce.sh --db census.sqlite guardian urls.txt --out guardian_raw --depth 1 --max-pages 25
```

## Full pipeline

```bash
./run_all.sh
```

## Output

Guardian creates:

```text
guardian_raw/html/*.html       # exact fetched source bytes
guardian_raw/text/*.txt        # extracted readable text
guardian_raw/meta/*.json       # per-source metadata + discovered links
guardian_raw/guardian_manifest.jsonl
guardian_raw/guardian_summary.json
```

The ledger also receives extracted claims/entities/events and reports:

```text
census.sqlite
reports/evidence_report.md
reports/evidence_graph.json
reports/evidence_graph.graphml
reports/entity_resolution_candidates.json
reports/hash_chain_verification.json
```

## Commands

```bash
./ce.sh init --db census.sqlite
./ce.sh ingest evidence_inbox --db census.sqlite
./ce.sh guardian urls.txt --out guardian_raw --db census.sqlite
./ce.sh report --db census.sqlite --out reports/evidence_report.md
./ce.sh graph --db census.sqlite --format graphml --out reports/evidence_graph.graphml
./ce.sh verify-chain --db census.sqlite
```

## What Guardian now actually does

- Reads explicit operator URL lists.
- Fetches pages with a named user agent.
- Saves raw HTML bytes.
- Extracts readable text.
- Extracts links.
- Saves SHA-256 hashes.
- Writes manifest JSONL.
- Ingests extracted text into the evidence ledger.
- Adds claims, entities, events, verification tasks, graph links, and reports.

