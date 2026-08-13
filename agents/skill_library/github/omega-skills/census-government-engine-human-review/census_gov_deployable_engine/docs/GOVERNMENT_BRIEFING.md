# Government Briefing — CENSUS Civic Witness Engine

## Executive summary

CENSUS is a deployable civic witness engine. It converts mixed historical records into auditable event ledgers, then separates strong canon from witness material, repair queues, and private records. It is designed for transparency, service-delivery insight, record reconciliation, and oversight-reviewed pilot deployment.

This handoff package contains a working local/API engine, redacted demonstration data, audit reports, and deployment instructions.

## Problem

Government records often exist in separate systems: identity, locality, service delivery, incidents, housing, education, household records, and communications. Fragmentation makes it hard to see patterns over time. It also makes it easy for weak claims, missing dates, bad source provenance, and private information to be mixed together.

## CENSUS answer

CENSUS creates a controlled promotion ladder:

```text
candidate
  → source_confirmed / source_confirmed_fuzzy
  → inferred_or_unconfirmed
  → source_missing
  → sensitive_redacted / sensitive_source_confirmed
  → duplicate
```

The current v5 finish state then separates:

```text
canon_core
source_filename_date_witness
date_repair_required
private_canon_candidate
private_only_sensitive
unconfirmed_review
noise_or_log_review
line_evidence_missing
fuzzy_witness_only
```

## Current evidence state

From the one-night closeout:

- `canon_core`: 357 records.
- `source_filename_date_witness`: 1,392 records.
- `date_repair_required`: 428 records.
- `private_canon_candidate`: 26 records.
- `private_only_sensitive`: 24 records.
- `unconfirmed_review`: 15 records.
- `noise_or_log_review`: 8 records.
- `line_evidence_missing`: 7 records.
- `fuzzy_witness_only`: 3 records.

## Pilot proposal

A lawful pilot should begin as a voluntary, oversight-reviewed, non-adverse-decision deployment.

Recommended pilot:

1. 1,000–10,000 voluntary records or synthetic/government-approved test records.
2. Independent legal/ethics oversight.
3. Citizen access to their own generated reports.
4. Correction and appeal process.
5. No automated adverse decisions.
6. Full audit logs.
7. Five-year sunset/review condition before any scale-up.

## Deployment options

1. Local laptop/server: Python CLI.
2. Department server: Docker Compose.
3. Internal API: FastAPI service behind government network controls.
4. Offline review: redacted JSONL + markdown reports.

## Immediate demonstration

```bash
python -m census_engine.cli manifest
python -m census_engine.cli report --out out/CENSUS_ENGINE_REPORT.md
uvicorn census_engine.api:app --host 0.0.0.0 --port 8080
```

