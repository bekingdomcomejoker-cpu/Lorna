# Unified Spec Implementation Map

Source target: **Census Engine: Unified System Specification (v3.0)**

## Mapped components

| Spec component | Implemented file |
|---|---|
| Local History Extractor | `history_extractor.py`, `census_engine/history_extractor.py` |
| Guardian Sensor | `omega_guardian_engine.py`, `census_engine/guardian.py` |
| Verification Loop | `review_canon.py`, `census_engine/review.py` |
| Local JSONL Flat Files | `~/.omega/census/*.jsonl` |
| Local memory backbone | `~/.omega/ledger.db` |
| MPAM | `census_engine/mpam.py` |
| Source registry | `sources` table + `source_registry.py` |
| Human canon promotion | `canon_reviews` table + review CLI |

## Completion condition

The engine is complete enough to run locally when these commands succeed:

```bash
census init
census extract --input examples --out ~/.omega/census/history_events.jsonl
census guardian --input examples --out ~/.omega/census/guardian_events.jsonl
census review --limit 5
census report --out ~/.omega/census/CENSUS_REPORT.md
```
