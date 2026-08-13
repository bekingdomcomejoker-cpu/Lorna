# Census Engine v4.2 — Terminal Kit

This package is terminal-first. It is no longer just a demo script.

Drop files into `evidence_inbox/`, add explicit public URLs to `urls.txt`, then run one command.

## Linux / Termux / WSL

```bash
cd census_engine_v4_2_terminal_kit
chmod +x install.sh run_all.sh ce.sh scripts/*.sh
./install.sh
./run_all.sh
```

## Windows PowerShell

```powershell
cd census_engine_v4_2_terminal_kit
powershell -ExecutionPolicy Bypass -File .\install.ps1
powershell -ExecutionPolicy Bypass -File .\run_all.ps1
```

## Windows CMD

```bat
cd census_engine_v4_2_terminal_kit
run_all.bat
```

## One-command pipeline

`run_all.sh` / `run_all.ps1` performs:

1. create/open `census.sqlite`
2. ingest everything in `evidence_inbox/`
3. fetch every explicit URL listed in `urls.txt`
4. extract dates, entities, case refs, URLs, SA ID patterns, places, organizations
5. create claims/events/entities
6. append source and claim records to the hash chain
7. generate markdown report
8. export JSON graph
9. export GraphML graph
10. run entity-resolution candidates
11. verify the hash chain

Outputs:

- `census.sqlite`
- `reports/evidence_report.md`
- `reports/evidence_graph.json`
- `reports/evidence_graph.graphml`
- `reports/entity_resolution_candidates.json`
- `reports/hash_chain_verification.json`
- `logs/*.json`

## Direct commands

Use the wrapper:

```bash
./ce.sh init --db census.sqlite
./ce.sh ingest evidence_inbox --db census.sqlite
./ce.sh fetch-url "https://example.com/public-record" --label "Source label" --db census.sqlite
./ce.sh fetch-list urls.txt --db census.sqlite
./ce.sh list sources --db census.sqlite
./ce.sh list claims --db census.sqlite
./ce.sh resolve --db census.sqlite
./ce.sh report --db census.sqlite --out reports/evidence_report.md
./ce.sh graph --db census.sqlite --format graphml --out reports/evidence_graph.graphml
./ce.sh verify-chain --db census.sqlite
```

Or call Python directly. `--db` now works before or after the subcommand:

```bash
python -m census_engine --db census.sqlite ingest evidence_inbox
python -m census_engine ingest evidence_inbox --db census.sqlite
```

## URL file format

`urls.txt` accepts one URL per line:

```text
https://example.com/record
https://example.com/record2 | My label for this record
```

## Evidence inbox

Accepted local inputs include:

- `.txt`
- `.md`
- `.csv`
- `.json`
- `.html`
- `.xml`
- `.log`
- `.rtf`

For PDFs/DOCX, export to text first, then place the text version in `evidence_inbox/`.

## What this version fixes

- Adds terminal scripts instead of only `run_demo.sh`.
- Adds full pipeline script.
- Adds URL batch fetch command.
- Adds `run` command for all-in-one processing.
- Fixes CLI argument order so `--db` works after subcommands.
- Removes demo database from the package.
- Creates logs/reports/exports automatically.


## v4.3 Guardian restored

Run:

```bash
./ce.sh --db census.sqlite guardian urls.txt --out guardian_raw
```

This preserves raw HTML, extracted text, SHA-256 hashes, metadata JSON, manifest JSONL, and ingests extracted text into the local ledger. See README_GUARDIAN_TERMUX.md.
