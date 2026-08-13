import json, difflib
from .db import connect

def resolve_candidates(db_path, out_path):
    con = connect(db_path)
    rows = [dict(r) for r in con.execute("SELECT entity_id, entity_type, value, normalized, evidence_count FROM entities")]
    out = []
    for i, a in enumerate(rows):
        for b in rows[i+1:]:
            if a["entity_type"] != b["entity_type"]:
                continue
            ratio = difflib.SequenceMatcher(None, a["normalized"], b["normalized"]).ratio()
            if ratio >= 0.84 and a["normalized"] != b["normalized"]:
                out.append({"a": a, "b": b, "score": ratio})
    con.close()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    return out_path
