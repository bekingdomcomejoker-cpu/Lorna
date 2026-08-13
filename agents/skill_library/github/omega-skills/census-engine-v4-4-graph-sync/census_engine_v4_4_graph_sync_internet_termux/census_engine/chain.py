import json, hashlib
from .db import connect

def verify_chain(db_path, out_path=None):
    con = connect(db_path)
    rows = [dict(r) for r in con.execute("SELECT * FROM chain ORDER BY seq")]
    prev = ""
    ok = True
    errors = []
    for r in rows:
        expected = hashlib.sha256((prev + r["record_hash"]).encode("utf-8")).hexdigest()
        if r["prev_hash"] != prev or r["chain_hash"] != expected:
            ok = False
            errors.append({"seq": r["seq"], "expected_prev": prev, "actual_prev": r["prev_hash"], "expected_chain": expected, "actual_chain": r["chain_hash"]})
        prev = r["chain_hash"]
    con.close()
    result = {"ok": ok, "records": len(rows), "errors": errors, "tip": prev}
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    return result
