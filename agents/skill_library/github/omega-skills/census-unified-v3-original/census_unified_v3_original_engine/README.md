# Census Engine — Unified System Specification v3.0

Author / Architect: Dominique Snyman  
Implementation support: Node 1 / The Architect

This package implements the original v3.0 build target:

- `history_extractor.py` — local history extraction from supplied files / exports.
- `omega_guardian_engine.py` — local/public/supplied source sensor intake.
- `review_canon.py` — Termux-first human verification loop.
- `census_engine/ledger.py` — SQLite memory backbone.
- `census_engine/mpam.py` — Moment-Presence Alphabet Mapping support.
- `census_engine/source_registry.py` — source registry and hashes.
- `census_engine/entity_resolver.py` — conservative entity/date extraction.
- `census_engine/report.py` — canon/witness/private report export.
- `census_engine/cli.py` — unified command interface.

## Minimal Termux install

```bash
cd ~/storage/downloads
unzip -o CENSUS_UNIFIED_V3_ORIGINAL_ENGINE_2026-06-07.zip -d ~/omega_apps/census_unified_v3
cd ~/omega_apps/census_unified_v3/census_unified_v3_original_engine
bash install_termux.sh
```

No venv is required. No pip is required for the CLI path.

## Operational flow

```bash
census init
census extract --input ~/storage/downloads/chatgpt_export --out ~/.omega/census/history_events.jsonl
census guardian --input ~/storage/downloads/source_files --out ~/.omega/census/guardian_events.jsonl
census review --ledger ~/.omega/ledger.db --limit 25
census report --out ~/.omega/census/CENSUS_REPORT.md
```

## What this engine does

It builds a local evidence ledger from files you supply, local exports, public/source files you place in folders, and optional public URL fetches you explicitly provide. It promotes records through human review into canon/witness/reject/private.

## What is intentionally not included

No credential bypass. No hidden database access. No evasion logic. No unauthorized account access. Real government/Guard.set integration requires an actual schema, export, endpoint, or authorized connector.
