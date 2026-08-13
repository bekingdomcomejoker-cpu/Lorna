# Build Notes

Built: 2026-06-07T21:57:42.658508
Package: Census Engine v4.4 Graph Sync + Internet Guardian Termux Kit

Implemented:
- Internet Guardian fetcher using Python stdlib urllib.
- Same-domain crawl by depth/max-pages.
- Raw HTML/text/meta preservation.
- SHA-256 source/artifact hashing.
- SQLite run ledger.
- SQLite graph node/edge tables.
- `sync-graph` command.
- Per-run JSON and GraphML exports.
- Per-run `MANIFEST.md`.
- Report writer.
- Entity extraction, claim extraction, event extraction.
- Hash-chain verification.
- Interactive CATTER phone script.
- Local self-test script for Termux: `./scripts/selftest_local.sh`.

Note:
The build was packaged without running internet fetches from this environment. The included Termux code fetches real HTTP/HTTPS URLs when run on the phone.
