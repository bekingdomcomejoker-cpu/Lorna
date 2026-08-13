# Build Notes — What Changed from v3.0

The v3.0 spec promised more than the code delivered. v4.1 implements the missing core mechanics that are actually buildable in a local engine:

| v3.0 Claim | v4.1 Implementation |
|---|---|
| MPAM | `extractors/mpam.py`: dates, places, people, orgs, case refs, URLs, SA ID patterns, bucket scoring |
| Immutable ledger | SQLite + append-only hash chain + `verify-chain` |
| OSINT ingestion | explicit URL fetcher + local file ingestion + manual CSV/JSON adapters |
| Public-record verification | verification-task queue, URL/source registry, report fields |
| Entity resolution | normalized entity registry + alias table + fuzzy candidate matcher |
| Biographical/event ledger | claims + event candidates + source IDs + confidence |
| Graph intelligence | JSON + GraphML export |
| Human review | quarantine/canon/witness/rejected statuses + review console stub |
| Reporting | redacted markdown report with chain tip |

The remaining pieces require real external access or operator-provided data exports:

- CIPC director histories
- CCMA files/awards
- SAFLII pages/PDFs
- court records
- social-media exports/takeouts
- email/Drive documents

Those are handled by import/fetch adapters rather than invented.
