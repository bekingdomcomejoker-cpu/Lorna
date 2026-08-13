# CENSUS Human Verification Node

This is the missing final threshold between extraction and active canon.

The engine must not treat generated candidates as final truth merely because they were extracted. A human reviewer promotes records into active canon, witness, private, or reject states.

## Review commands

```bash
python -m census_engine.cli review --bucket canon_core --limit 25
python -m census_engine.cli review-status
python -m census_engine.cli export-reviewed --include canon --out out/human_reviewed_canon.jsonl
```

Termux shortcut:

```bash
python review_canon.py review --bucket canon_core --limit 25
```

## Decisions

- `canon`: verified enough for active working canon.
- `witness`: useful source/witness material, not final canon.
- `private`: valid but should remain private/local only.
- `reject`: not useful or not supported.
- `skip`: no decision yet.

## State model

Human decisions are append-only in:

```text
out/review_decisions.jsonl
```

The latest decision for a record wins. Exported reviewed canon is produced separately, so the original data files are not overwritten.

## Original mission alignment

CENSUS exists to convert raw history into a verified civic witness ledger. The human review node is the consent and verification threshold: automated extraction creates candidates, but human review creates canon.
