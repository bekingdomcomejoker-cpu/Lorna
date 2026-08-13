# Census Engine v4.2 — Termux Quick Start

This is the phone/Termux route. It is designed so you can copy the folder to Android storage, open Termux, and run a full local pipeline.

## 0. Put the package on the phone

Unzip the package somewhere you can reach from Termux, for example:

```bash
cd ~/storage/downloads
unzip CENSUS_ENGINE_V4_2_TERMINAL_KIT_2026-06-07.zip
cd census_engine_v4_2_terminal_kit
```

If `~/storage` does not exist yet:

```bash
termux-setup-storage
```

Approve the Android permission prompt, then reopen Termux if needed.

## 1. Install

```bash
chmod +x install.sh run_all.sh ce.sh scripts/*.sh
./install.sh
```

## 2. Add evidence

Put text evidence into:

```text
evidence_inbox/
```

Accepted local evidence types:

```text
.txt .md .csv .json .html .xml .log .rtf
```

For PDF/DOCX, export or copy the text first, then place the text version in `evidence_inbox/`.

## 3. Add public URLs

Edit `urls.txt`:

```bash
nano urls.txt
```

One URL per line:

```text
https://example.com/public-record
https://example.com/another-record | Optional source label
```

## 4. Run everything

```bash
./run_all.sh
```

This runs:

```text
init → ingest evidence_inbox → fetch urls.txt → report → graph exports → resolve → verify chain
```

## 5. Outputs

```text
census.sqlite
reports/evidence_report.md
reports/evidence_graph.json
reports/evidence_graph.graphml
reports/entity_resolution_candidates.json
reports/hash_chain_verification.json
logs/*.json
```

## 6. Direct commands

```bash
./ce.sh init --db census.sqlite
./ce.sh ingest evidence_inbox --db census.sqlite
./ce.sh fetch-list urls.txt --db census.sqlite
./ce.sh fetch-url "https://example.com/public-record" --label "Source label" --db census.sqlite
./ce.sh report --db census.sqlite --out reports/evidence_report.md
./ce.sh graph --db census.sqlite --format graphml --out reports/evidence_graph.graphml
./ce.sh graph --db census.sqlite --format json --out reports/evidence_graph.json
./ce.sh resolve --db census.sqlite
./ce.sh verify-chain --db census.sqlite
```

## 7. Move reports back to Downloads

```bash
mkdir -p ~/storage/downloads/census_reports
cp -r reports/* ~/storage/downloads/census_reports/
cp census.sqlite ~/storage/downloads/census_reports/
```

## 8. Reset database only when you mean it

```bash
rm census.sqlite
./ce.sh init --db census.sqlite
```

## Notes

This kit does not need cloud storage to run. It creates a local SQLite evidence ledger and local report/export files.
