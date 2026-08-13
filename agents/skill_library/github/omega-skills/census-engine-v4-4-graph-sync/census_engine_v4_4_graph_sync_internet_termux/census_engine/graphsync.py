import json
from pathlib import Path
from .db import connect, stable_id, upsert_graph_node, insert_graph_edge, append_chain, now

def sync_graph(db_path, run_id, raw_dir=None, reports_dir=None):
    con = connect(db_path)
    run = con.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
    if not run:
        con.execute("INSERT OR REPLACE INTO runs(run_id,created_at,raw_path,report_path,status,notes) VALUES(?,?,?,?,?,?)", (run_id, now(), raw_dir or "", reports_dir or "", "SYNCING", "created by sync-graph"))
    run_node = "run:" + run_id
    upsert_graph_node(con, run_id, "RUN", run_node, run_id, {"run_id": run_id, "raw_dir": raw_dir, "reports_dir": reports_dir})
    for s in con.execute("SELECT * FROM sources WHERE run_id=?", (run_id,)):
        source_node = "source:" + s["source_id"]
        target_node = "target:" + stable_id("target", run_id, s["url"])
        upsert_graph_node(con, run_id, "TARGET", target_node, s["label"] or s["url"], {"url": s["url"], "label": s["label"]})
        upsert_graph_node(con, run_id, "SOURCE", source_node, s["title"] or s["url"], dict(s))
        insert_graph_edge(con, run_id, run_node, target_node, "RUN_SEEDED_TARGET", {})
        insert_graph_edge(con, run_id, target_node, source_node, "TARGET_FETCHED_SOURCE", {"depth": s["depth"], "parent_url": s["parent_url"]})
        if s["sha256"]:
            hash_node = "hash:" + s["sha256"]
            upsert_graph_node(con, run_id, "HASH", hash_node, s["sha256"][:16], {"algorithm": "sha256", "digest": s["sha256"]})
            insert_graph_edge(con, run_id, source_node, hash_node, "ARTIFACT_HAS_HASH", {})
    for a in con.execute("SELECT * FROM artifacts WHERE run_id=?", (run_id,)):
        artifact_node = "artifact:" + a["artifact_id"]
        source_node = "source:" + a["source_id"]
        upsert_graph_node(con, run_id, "ARTIFACT", artifact_node, f"{a['artifact_type']}:{Path(a['path']).name}", dict(a))
        insert_graph_edge(con, run_id, source_node, artifact_node, "SOURCE_PRODUCED_ARTIFACT", {"artifact_type": a["artifact_type"]})
        if a["sha256"]:
            hash_node = "hash:" + a["sha256"]
            upsert_graph_node(con, run_id, "HASH", hash_node, a["sha256"][:16], {"algorithm": "sha256", "digest": a["sha256"]})
            insert_graph_edge(con, run_id, artifact_node, hash_node, "ARTIFACT_HAS_HASH", {})
    for e in con.execute("SELECT * FROM entities WHERE run_id=?", (run_id,)):
        entity_node = "entity:" + e["entity_id"]
        upsert_graph_node(con, run_id, e["entity_type"], entity_node, e["value"], dict(e))
        if e["first_source_id"]:
            insert_graph_edge(con, run_id, "source:" + e["first_source_id"], entity_node, "SOURCE_MENTIONS_ENTITY", {"count": e["evidence_count"]})
    for c in con.execute("SELECT * FROM claims WHERE run_id=?", (run_id,)):
        claim_node = "claim:" + c["claim_id"]
        upsert_graph_node(con, run_id, "CLAIM", claim_node, c["claim_text"][:120], dict(c))
        insert_graph_edge(con, run_id, "source:" + c["source_id"], claim_node, "CLAIM_SUPPORTED_BY_SOURCE", {"grade": c["evidence_grade"]})
        if c["needs_verification"]:
            task_id = stable_id("task", run_id, c["claim_id"])
            task_node = "task:" + task_id
            upsert_graph_node(con, run_id, "VERIFICATION_TASK", task_node, "Verify claim", {"claim_id": c["claim_id"], "status": "OPEN"})
            insert_graph_edge(con, run_id, claim_node, task_node, "CLAIM_NEEDS_VERIFICATION", {})
    for ev in con.execute("SELECT * FROM events WHERE run_id=?", (run_id,)):
        event_node = "event:" + ev["event_id"]
        upsert_graph_node(con, run_id, "EVENT", event_node, ev["event_date"] or ev["event_text"][:80], dict(ev))
        insert_graph_edge(con, run_id, "source:" + ev["source_id"], event_node, "EVENT_SUPPORTED_BY_SOURCE", {"grade": ev["evidence_grade"]})
    if reports_dir:
        rp = Path(reports_dir)
        rp.mkdir(parents=True, exist_ok=True)
        for path in rp.glob("*"):
            if path.is_file():
                sid = stable_id("section", run_id, path.name)
                con.execute("INSERT OR REPLACE INTO report_sections(section_id,run_id,report_path,title,created_at) VALUES(?,?,?,?,?)", (sid, run_id, str(path), path.name, now()))
                node = "report:" + sid
                upsert_graph_node(con, run_id, "REPORT_SECTION", node, path.name, {"path": str(path)})
                insert_graph_edge(con, run_id, run_node, node, "RUN_HAS_REPORT_SECTION", {})
    append_chain(con, run_id, "graph_sync", "graph:" + run_id, {"run_id": run_id, "synced_at": now()})
    con.execute("UPDATE runs SET status=?, report_path=? WHERE run_id=?", ("GRAPH_SYNCED", reports_dir or "", run_id))
    con.commit()
    counts = {
        "nodes": con.execute("SELECT COUNT(*) c FROM graph_nodes WHERE run_id=?", (run_id,)).fetchone()["c"],
        "edges": con.execute("SELECT COUNT(*) c FROM graph_edges WHERE run_id=?", (run_id,)).fetchone()["c"],
    }
    con.close()
    return counts
