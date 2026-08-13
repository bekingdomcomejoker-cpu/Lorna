# Deploy Now

## Local

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m census_engine.cli manifest
python -m census_engine.cli report --out out/CENSUS_ENGINE_REPORT.md
```

## API

```bash
uvicorn census_engine.api:app --host 0.0.0.0 --port 8080
```

## Docker

```bash
docker compose up --build
```

## First review route

1. Read `docs/GOVERNMENT_BRIEFING.md`.
2. Read `docs/ORIGINAL_MISSION.md`.
3. Read `docs/LEGAL_AND_ETHICAL_GUARDRAILS.md`.
4. Run `python -m census_engine.cli report`.
5. Open `out/CENSUS_ENGINE_REPORT.md`.



## Human review closeout

```bash
python -m census_engine.cli review --bucket canon_core --limit 25
python -m census_engine.cli review-status
python -m census_engine.cli export-reviewed --include canon --out out/human_reviewed_canon.jsonl
```
