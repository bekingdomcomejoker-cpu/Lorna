from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .engine import CensusEngine

app = FastAPI(
    title="CENSUS Civic Witness Engine",
    version="1.0.0-gov-handoff",
    description="Government-handoff prototype for source-grounded civic witness, canon/witness separation, and audit reporting.",
)
engine = CensusEngine()


@app.get("/health")
def health():
    return {"status": "ok", "engine": "CENSUS", "mode": "civic_witness"}


@app.get("/manifest")
def manifest():
    return engine.manifest()


@app.get("/report")
def report():
    return engine.build_report().model_dump()


@app.get("/report.md")
def report_markdown():
    return {"markdown": engine.render_markdown_report()}


@app.get("/buckets/{bucket}")
def bucket_records(bucket: str, limit: int = 20, offset: int = 0):
    try:
        records = engine.load_bucket(bucket, limit=limit, offset=offset)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [r.model_dump() for r in records]
