# Technical Architecture

## Pipeline

```text
Source Records
  → extractor
  → event candidates
  → source confirmation
  → line evidence recovery
  → date/speaker review
  → promotion ledger
  → canon/witness/private separation
  → witness report / API
```

## Current package layer

This deployment package starts after v5 loop closure. It does not rerun the whole extraction chain by default. It serves the closed promotion ledger and provides a report/API surface.

## Buckets served by the engine

- `canon_core`: strongest non-sensitive working canon.
- `source_filename_date_witness`: source-supported witness records with weak date lock.
- `date_repair_required`: records requiring date improvement.
- `unconfirmed_review`: weak/unconfirmed review queue.

Private queues are not served raw.

## API endpoints

- `GET /health`
- `GET /manifest`
- `GET /report`
- `GET /report.md`
- `GET /buckets/{bucket}?limit=20&offset=0`

## CLI commands

```bash
python -m census_engine.cli manifest
python -m census_engine.cli report --out out/CENSUS_ENGINE_REPORT.md
python -m census_engine.cli list --bucket canon_core --limit 5
```



## Human-in-the-loop verification node

The review node is the final promotion gate. Automated extraction and v5 tiering remain evidence preparation. A human reviewer makes the active ledger decision through the CLI and the engine stores append-only decisions in `out/review_decisions.jsonl`. This prevents candidate data from silently becoming canon.
