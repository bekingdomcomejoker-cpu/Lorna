import sqlite3, json, hashlib, datetime

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  created_at TEXT,
  target_count INTEGER DEFAULT 0,
  raw_path TEXT,
  report_path TEXT,
  status TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS sources (
  source_id TEXT PRIMARY KEY,
  run_id TEXT,
  url TEXT,
  label TEXT,
  fetched_at TEXT,
  status INTEGER,
  content_type TEXT,
  title TEXT,
  html_path TEXT,
  text_path TEXT,
  meta_path TEXT,
  sha256 TEXT,
  parent_url TEXT,
  depth INTEGER,
  error TEXT
);

CREATE TABLE IF NOT EXISTS artifacts (
  artifact_id TEXT PRIMARY KEY,
  run_id TEXT,
  source_id TEXT,
  artifact_type TEXT,
  path TEXT,
  sha256 TEXT,
  created_at TEXT,
  bytes INTEGER
);

CREATE TABLE IF NOT EXISTS hashes (
  hash_id TEXT PRIMARY KEY,
  run_id TEXT,
  source_id TEXT,
  artifact_id TEXT,
  algorithm TEXT,
  digest TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS entities (
  entity_id TEXT PRIMARY KEY,
  run_id TEXT,
  entity_type TEXT,
  value TEXT,
  normalized TEXT,
  first_source_id TEXT,
  evidence_count INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS aliases (
  alias_id TEXT PRIMARY KEY,
  entity_id TEXT,
  alias TEXT,
  source_id TEXT
);

CREATE TABLE IF NOT EXISTS claims (
  claim_id TEXT PRIMARY KEY,
  run_id TEXT,
  source_id TEXT,
  claim_text TEXT,
  evidence_grade TEXT,
  created_at TEXT,
  needs_verification INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS events (
  event_id TEXT PRIMARY KEY,
  run_id TEXT,
  source_id TEXT,
  event_date TEXT,
  event_text TEXT,
  evidence_grade TEXT
);

CREATE TABLE IF NOT EXISTS verification_tasks (
  task_id TEXT PRIMARY KEY,
  run_id TEXT,
  claim_id TEXT,
  entity_id TEXT,
  task_text TEXT,
  status TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS report_sections (
  section_id TEXT PRIMARY KEY,
  run_id TEXT,
  report_path TEXT,
  title TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS graph_nodes (
  node_id TEXT PRIMARY KEY,
  run_id TEXT,
  node_type TEXT,
  label TEXT,
  data_json TEXT
);

CREATE TABLE IF NOT EXISTS graph_edges (
  edge_id TEXT PRIMARY KEY,
  run_id TEXT,
  source_node TEXT,
  target_node TEXT,
  edge_type TEXT,
  data_json TEXT
);

CREATE TABLE IF NOT EXISTS chain (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT,
  record_type TEXT,
  record_id TEXT,
  record_hash TEXT,
  prev_hash TEXT,
  chain_hash TEXT,
  created_at TEXT
);
"""

def connect(db_path):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con

def init_db(db_path):
    con = connect(db_path)
    con.executescript(SCHEMA)
    con.commit()
    con.close()

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def stable_id(prefix, *parts):
    h = hashlib.sha256()
    for p in parts:
        h.update(str(p).encode("utf-8", "ignore"))
        h.update(b"\0")
    return prefix + "_" + h.hexdigest()[:24]

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 256), b""):
            h.update(chunk)
    return h.hexdigest()

def append_chain(con, run_id, record_type, record_id, payload):
    payload_s = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    record_hash = hashlib.sha256(payload_s.encode("utf-8")).hexdigest()
    row = con.execute("SELECT chain_hash FROM chain ORDER BY seq DESC LIMIT 1").fetchone()
    prev = row["chain_hash"] if row else ""
    chain_hash = hashlib.sha256((prev + record_hash).encode("utf-8")).hexdigest()
    con.execute(
        "INSERT INTO chain(run_id,record_type,record_id,record_hash,prev_hash,chain_hash,created_at) VALUES(?,?,?,?,?,?,?)",
        (run_id, record_type, record_id, record_hash, prev, chain_hash, now()),
    )
    return chain_hash

def upsert_graph_node(con, run_id, node_type, node_id, label, data):
    con.execute(
        "INSERT OR REPLACE INTO graph_nodes(node_id,run_id,node_type,label,data_json) VALUES(?,?,?,?,?)",
        (node_id, run_id, node_type, label, json.dumps(data, ensure_ascii=False, sort_keys=True)),
    )

def insert_graph_edge(con, run_id, source_node, target_node, edge_type, data=None):
    data = data or {}
    edge_id = stable_id("edge", run_id, source_node, target_node, edge_type, json.dumps(data, sort_keys=True))
    con.execute(
        "INSERT OR IGNORE INTO graph_edges(edge_id,run_id,source_node,target_node,edge_type,data_json) VALUES(?,?,?,?,?,?)",
        (edge_id, run_id, source_node, target_node, edge_type, json.dumps(data, ensure_ascii=False, sort_keys=True)),
    )
    return edge_id
