from pathlib import Path
from .db import connect, now

def write_report(db_path, out_path, run_id=None):
    con = connect(db_path)
    params = (run_id,) if run_id else ()
    where = "WHERE run_id=?" if run_id else ""
    out = ["# Census Engine Evidence Report", "", f"Generated: {now()}"]
    if run_id:
        out.append(f"Run ID: {run_id}")
    out += ["", "## Runs"]
    for r in con.execute(f"SELECT * FROM runs {where} ORDER BY created_at DESC", params):
        out.append(f"- **{r['run_id']}** — {r['status']} — targets: {r['target_count']} — raw: `{r['raw_path']}`")
    out += ["", "## Sources"]
    for s in con.execute(f"SELECT * FROM sources {where} ORDER BY fetched_at", params):
        status = s["status"] if s["status"] is not None else "ERROR"
        out.append(f"- [{status}] {s['title'] or s['url']} — {s['url']}")
        out.append(f"  - SHA-256: `{s['sha256'] or ''}`")
        if s["error"]:
            out.append(f"  - Error: {s['error']}")
    out += ["", "## Entities"]
    for e in con.execute(f"SELECT * FROM entities {where} ORDER BY evidence_count DESC, entity_type, value LIMIT 300", params):
        out.append(f"- **{e['entity_type']}**: {e['value']} — evidence count: {e['evidence_count']}")
    out += ["", "## Claims"]
    for c in con.execute(f"SELECT * FROM claims {where} ORDER BY created_at LIMIT 300", params):
        out.append(f"- [{c['evidence_grade']}] {c['claim_text']}")
    out += ["", "## Events"]
    for ev in con.execute(f"SELECT * FROM events {where} ORDER BY event_date LIMIT 200", params):
        out.append(f"- {ev['event_date']}: {ev['event_text']}")
    out += ["", "## Verification Tasks"]
    for t in con.execute(f"SELECT * FROM verification_tasks {where} ORDER BY created_at LIMIT 300", params):
        out.append(f"- [{t['status']}] {t['task_text']} — claim: {t['claim_id']}")
    con.close()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text("\n".join(out), encoding="utf-8")
    return out_path
