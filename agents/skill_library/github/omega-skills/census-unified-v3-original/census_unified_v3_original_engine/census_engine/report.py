from __future__ import annotations
from pathlib import Path
from .ledger import connect, init_db, status_counts, DEFAULT_DB

def write_report(out: Path, db_path: Path = DEFAULT_DB):
    init_db(db_path)
    con = connect(db_path)
    counts = status_counts(db_path)
    rows = con.execute("""
        SELECT id,event_date,event_type,source_path,line_start,line_end,speaker,text,review_status,privacy_status,mpam_axis,pressure_score
        FROM sensor_events ORDER BY review_status,event_date,ts LIMIT 500
    """).fetchall()
    con.close()

    out = Path(out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# CENSUS / SENSUS Report")
    lines.append("")
    lines.append("## Review Status Counts")
    for k, v in counts.items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Event Sample")
    for r in rows:
        d = dict(r)
        lines.append(f"### {d['event_date']} — {d['event_type']} — {d['review_status']}")
        lines.append(f"- ID: `{d['id']}`")
        lines.append(f"- Source: `{d['source_path']}:L{d['line_start']}-L{d['line_end']}`")
        lines.append(f"- Speaker: {d['speaker']}")
        lines.append(f"- Axis: {d['mpam_axis']} | Pressure: {d['pressure_score']}")
        lines.append("")
        lines.append(d["text"] or "")
        lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out
