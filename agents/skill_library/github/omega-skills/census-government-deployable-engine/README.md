# CENSUS Government Deployment Package

**Status:** deployable civic-witness prototype, v1 handoff.

This package turns the closed CENSUS v5 ledger into a runnable engine for review, pilot deployment, and government briefing. It does **not** claim supernatural certainty, deterministic control, or authority over citizens. It is a transparent evidence/witness engine: it ingests records, preserves source boundaries, classifies civic signals, separates canon/witness/private queues, and emits audit-ready reports.

## What this package contains

- `census_engine/` — working Python engine and optional FastAPI server.
- `data/` — redacted CENSUS one-night closeout queues.
- `docs/` — government briefing, original mission, legal safeguards, pilot plan.
- `scripts/` — local run scripts.
- `tests/` — basic smoke tests.
- `docker-compose.yml` and `Dockerfile` — container deployment.

## Fast local run

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m census_engine.cli manifest
python -m census_engine.cli report --out out/CENSUS_ENGINE_REPORT.md
```

## API run

```bash
uvicorn census_engine.api:app --host 0.0.0.0 --port 8080
```

Open:

```text
http://localhost:8080/health
http://localhost:8080/manifest
http://localhost:8080/buckets/canon_core?limit=5
```

## Docker run

```bash
docker compose up --build
```

## Government handoff rule

Do not deploy this as a coercive surveillance or enforcement system. The intended lawful deployment is:

1. voluntary pilot first,
2. independent oversight,
3. citizen access to their own records,
4. appeal/correction routes,
5. audit logs,
6. privacy separation,
7. no automated denial of services, rights, employment, credit, policing, housing, or benefits.

