# Build Notes — v4.2 Terminal Kit

Created because v4.1 was too demo-shaped. v4.2 adds terminal-first execution.

## Added

- `install.sh`
- `run_all.sh`
- `ce.sh`
- `install.ps1`
- `run_all.ps1`
- `ce.ps1`
- `run_all.bat`
- `scripts/00_install_termux_linux.sh`
- `scripts/01_init.sh`
- `scripts/02_ingest_inbox.sh`
- `scripts/03_fetch_urls.sh`
- `scripts/04_report.sh`
- `scripts/05_graphs.sh`
- `scripts/06_resolve.sh`
- `scripts/07_verify_chain.sh`
- `scripts/08_full_pipeline.sh`
- `evidence_inbox/`
- `urls.txt`

## CLI changes

- Added `fetch-list`.
- Added `run` all-in-one pipeline.
- Fixed `--db` so it works before or after subcommands.

## Run target

Linux/Termux/WSL:

```bash
./install.sh
./run_all.sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
powershell -ExecutionPolicy Bypass -File .\run_all.ps1
```
