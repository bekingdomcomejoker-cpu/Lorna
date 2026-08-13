# Census Engine v4.1 — Full Evidence Engine

This is the buildable engine body: ingestion, source hashing, MPAM-style extraction, entity registry, evidence grading, verification tasks, hash-chain ledger, graph export, and report generation.

It does **not** pretend to access private government databases or paid registries by magic. It creates adapters where records can be imported, fetched by explicit URL, or loaded from CSV/JSON/TXT exports.

## Quick start

```bash
cd census_engine_v4_1_full
python -m census_engine --db demo.sqlite init
python -m census_engine --db demo.sqlite ingest examples/sample_notes.txt
python -m census_engine --db demo.sqlite report --out reports/demo_report.md
python -m census_engine --db demo.sqlite graph --out reports/demo_graph.json
python -m census_engine --db demo.sqlite verify-chain
```

## What v4.1 now implements

- Local file ingestion for TXT/MD/CSV/JSON/HTML/XML/LOG/RTF.
- Explicit public URL fetcher for a URL the operator supplies.
- Source registry with SHA-256 content hashes and redacted previews.
- MPAM-style extraction of dates, places, people, organizations, case references, URLs, and SA ID patterns.
- SA ID checksum validation and birthdate parsing utility.
- Evidence grading: public-record claim, press-report claim, personal-witness claim, sensitive witness, unverified.
- SQLite ledger with sources, entities, aliases, claims, events, relations, verification tasks.
- Append-only hash chain for every source/claim/event/relation.
- Chain verification command.
- Candidate entity-resolution report using fuzzy matching.
- Markdown evidence report.
- JSON and GraphML graph exports for Gephi/yEd/Neo4j import.
- CIPC/CCMA/manual-record import hooks through CSV/JSON/TXT files.

## Commands

```bash
python -m census_engine --db census.sqlite init
python -m census_engine --db census.sqlite ingest PATH
python -m census_engine --db census.sqlite fetch-url URL --label "SAFLII Atlantis Motus"
python -m census_engine --db census.sqlite list claims
python -m census_engine --db census.sqlite resolve
python -m census_engine --db census.sqlite report --out reports/evidence.md
python -m census_engine --db census.sqlite graph --format graphml --out reports/evidence.graphml
python -m census_engine --db census.sqlite verify-chain
```

## Adapter pattern

For CIPC/CCMA/SAFLII/Motus/press records, store the record as one of:

- downloaded HTML/TXT/PDF-to-text export,
- manual CSV export,
- JSON record,
- explicit source URL fetched by `fetch-url`.

Then ingest it. The engine preserves the source hash, extracts claims, and opens verification tasks.
