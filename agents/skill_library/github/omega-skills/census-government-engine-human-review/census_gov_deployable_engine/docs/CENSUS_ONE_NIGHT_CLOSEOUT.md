# CENSUS ONE-NIGHT CLOSEOUT — NO LOOP, NO RISKY SHORTCUT

Generated: 2026-06-07T18:18:10.634808+00:00

## Decision

The automatic extraction/upgrade loop is closed at v5. No v6/v7 and no hidden prediction quiz. The original intention is preserved: build a usable history/canon from the evidence already supplied, keep witness material labeled, and keep private/sensitive records separated.

## Final ledger counts

- `source_filename_date_witness`: 1392
- `date_repair_required`: 428
- `canon_core`: 357
- `private_canon_candidate`: 26
- `private_only_sensitive`: 24
- `unconfirmed_review`: 15
- `noise_or_log_review`: 8
- `line_evidence_missing`: 7
- `fuzzy_witness_only`: 3

## Active use rule

- `canon_core` is the active working canon.
- `source_filename_date_witness` is witness material, not final date canon.
- `date_repair_required`, `line_evidence_missing`, and `unconfirmed_review` stay as queues.
- `private_*` stays sealed/local-only.

## What is complete tonight

- The usable canon has been exported: `CENSUS_CANON_CORE_357.md` and `.jsonl`.
- The witness tier has been separated: `CENSUS_SOURCE_FILENAME_DATE_WITNESS_1392.redacted.jsonl`.
- Date repair and missing-line queues have been separated without pretending they are done.
- Sensitive/private records have been sealed into an index.
- No additional risky action, scraping, credential use, or unbounded external data collection is included.

## What remains after tonight

Only targeted review remains, not another automated upgrade cycle:

- Repair dates only for records needed in an active task.
- Speaker-lock records only when they matter to a concrete claim.
- Recover or demote the 7 line-missing records when their source is available.

## Final action expectation

Use the 357 canon-core records as working memory. Treat the rest as labeled witness/repair/private queues. Stop expanding the system until there is a specific question that needs one of the queues.
