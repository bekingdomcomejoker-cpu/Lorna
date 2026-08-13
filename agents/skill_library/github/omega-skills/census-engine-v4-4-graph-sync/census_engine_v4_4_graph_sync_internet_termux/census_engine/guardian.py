import json, time, urllib.request
from pathlib import Path
from urllib.parse import urlparse
from .db import connect, init_db, stable_id, sha256_bytes, sha256_file, append_chain, now
from .extract import parse_html, same_domain, extract_entities, extract_claims, extract_events

USER_AGENT = "CensusEngineGuardian/4.4"

def read_url_list(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "|" in line:
                url, label = [x.strip() for x in line.split("|", 1)]
            else:
                url, label = line, ""
            if url.startswith(("http://", "https://")):
                rows.append((url, label))
    return rows

def safe_name(url, idx):
    host = urlparse(url).netloc.replace(":", "_")
    h = sha256_bytes(url.encode("utf-8"))[:12]
    return f"{idx:04d}_{host}_{h}"

def fetch_url(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return getattr(resp, "status", 200), resp.headers.get("content-type", ""), resp.geturl(), resp.read()

def run_guardian(db_path, url_file, run_id, out_dir, depth=0, max_pages=25, delay=0.25):
    init_db(db_path)
    out = Path(out_dir)
    html_dir, text_dir, meta_dir = out / "html", out / "text", out / "meta"
    for d in (html_dir, text_dir, meta_dir):
        d.mkdir(parents=True, exist_ok=True)

    con = connect(db_path)
    seeds = read_url_list(url_file)
    con.execute(
        "INSERT OR REPLACE INTO runs(run_id,created_at,target_count,raw_path,status,notes) VALUES(?,?,?,?,?,?)",
        (run_id, now(), len(seeds), str(out), "RUNNING", f"guardian depth={depth} max_pages={max_pages}"),
    )
    con.commit()

    queue = [(u, label, None, 0, u) for u, label in seeds]
    seen = set()
    manifest_path = out / "guardian_manifest.jsonl"
    fetched = 0
    errors = 0

    with open(manifest_path, "w", encoding="utf-8") as mf:
        while queue and fetched < max_pages:
            url, label, parent_url, d, root = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            fetched += 1
            base = safe_name(url, fetched)
            html_path = html_dir / f"{base}.html"
            text_path = text_dir / f"{base}.txt"
            meta_path = meta_dir / f"{base}.json"
            source_id = stable_id("source", run_id, url)
            try:
                status, content_type, final_url, data = fetch_url(url)
                raw_sha = sha256_bytes(data)
                raw_text = data.decode("utf-8", errors="replace")
                title, extracted_text, links = parse_html(raw_text, final_url)
                html_path.write_bytes(data)
                text_path.write_text(extracted_text, encoding="utf-8")
                meta = {
                    "run_id": run_id, "source_id": source_id, "url": url, "final_url": final_url,
                    "label": label, "parent_url": parent_url, "depth": d, "fetched_at": now(),
                    "status": status, "content_type": content_type, "title": title, "sha256": raw_sha,
                    "html_path": str(html_path), "text_path": str(text_path), "links": links,
                }
                meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
                con.execute(
                    """INSERT OR REPLACE INTO sources(source_id,run_id,url,label,fetched_at,status,content_type,title,html_path,text_path,meta_path,sha256,parent_url,depth,error)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (source_id, run_id, final_url, label, meta["fetched_at"], status, content_type, title, str(html_path), str(text_path), str(meta_path), raw_sha, parent_url, d, None),
                )
                for artifact_type, path in [("html", html_path), ("text", text_path), ("meta", meta_path)]:
                    aid = stable_id("artifact", run_id, source_id, artifact_type, path)
                    digest = sha256_file(path)
                    con.execute(
                        "INSERT OR REPLACE INTO artifacts(artifact_id,run_id,source_id,artifact_type,path,sha256,created_at,bytes) VALUES(?,?,?,?,?,?,?,?)",
                        (aid, run_id, source_id, artifact_type, str(path), digest, now(), path.stat().st_size),
                    )
                    hid = stable_id("hash", run_id, aid, digest)
                    con.execute(
                        "INSERT OR REPLACE INTO hashes(hash_id,run_id,source_id,artifact_id,algorithm,digest,created_at) VALUES(?,?,?,?,?,?,?)",
                        (hid, run_id, source_id, aid, "sha256", digest, now()),
                    )
                for etype, value in extract_entities(extracted_text):
                    norm = value.lower().strip()
                    eid = stable_id("entity", etype, norm)
                    row = con.execute("SELECT evidence_count FROM entities WHERE entity_id=?", (eid,)).fetchone()
                    if row:
                        con.execute("UPDATE entities SET evidence_count=evidence_count+1 WHERE entity_id=?", (eid,))
                    else:
                        con.execute(
                            "INSERT INTO entities(entity_id,run_id,entity_type,value,normalized,first_source_id,evidence_count) VALUES(?,?,?,?,?,?,?)",
                            (eid, run_id, etype, value, norm, source_id, 1),
                        )
                for claim in extract_claims(extracted_text):
                    cid = stable_id("claim", run_id, source_id, claim)
                    con.execute(
                        "INSERT OR IGNORE INTO claims(claim_id,run_id,source_id,claim_text,evidence_grade,created_at,needs_verification) VALUES(?,?,?,?,?,?,?)",
                        (cid, run_id, source_id, claim, "SOURCE_CLAIMED", now(), 1),
                    )
                    task_id = stable_id("task", run_id, cid)
                    con.execute(
                        "INSERT OR IGNORE INTO verification_tasks(task_id,run_id,claim_id,entity_id,task_text,status,created_at) VALUES(?,?,?,?,?,?,?)",
                        (task_id, run_id, cid, None, "Verify claim against primary or independent public source", "OPEN", now()),
                    )
                for event_date, event_text in extract_events(extracted_text):
                    evid = stable_id("event", run_id, source_id, event_date, event_text)
                    con.execute(
                        "INSERT OR IGNORE INTO events(event_id,run_id,source_id,event_date,event_text,evidence_grade) VALUES(?,?,?,?,?,?)",
                        (evid, run_id, source_id, event_date, event_text, "SOURCE_CLAIMED"),
                    )
                append_chain(con, run_id, "source", source_id, meta)
                con.commit()
                mf.write(json.dumps(meta, ensure_ascii=False) + "\n")
                mf.flush()
                if d < depth:
                    for link in links:
                        if len(queue) + fetched >= max_pages:
                            break
                        if same_domain(link, root) and link not in seen:
                            queue.append((link, "", final_url, d + 1, root))
                time.sleep(delay)
            except Exception as e:
                errors += 1
                meta = {"run_id": run_id, "source_id": source_id, "url": url, "label": label, "parent_url": parent_url, "depth": d, "fetched_at": now(), "error": repr(e)}
                meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
                con.execute(
                    """INSERT OR REPLACE INTO sources(source_id,run_id,url,label,fetched_at,status,content_type,title,html_path,text_path,meta_path,sha256,parent_url,depth,error)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (source_id, run_id, url, label, meta["fetched_at"], None, None, None, None, None, str(meta_path), None, parent_url, d, repr(e)),
                )
                append_chain(con, run_id, "source_error", source_id, meta)
                con.commit()
                mf.write(json.dumps(meta, ensure_ascii=False) + "\n")
                mf.flush()

    summary = {"run_id": run_id, "created_at": now(), "seed_count": len(seeds), "fetched_attempts": fetched, "errors": errors, "out_dir": str(out), "manifest": str(manifest_path)}
    (out / "guardian_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    con.execute("UPDATE runs SET status=?, notes=? WHERE run_id=?", ("FETCHED", json.dumps(summary, ensure_ascii=False), run_id))
    con.commit()
    con.close()
    return summary
