from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

DEFAULT_DB = Path("~/.omega/ledger.db").expanduser()

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    path TEXT,
    url TEXT,
    title TEXT,
    sha256 TEXT,
    source_type TEXT,
    created_at REAL,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS mission_logs (
    id TEXT PRIMARY KEY,
    ts REAL,
    event_type TEXT,
    status TEXT,
    message TEXT,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS sensor_events (
    id TEXT PRIMARY KEY,
    ts REAL,
    event_date TEXT,
    event_type TEXT,
    source_id TEXT,
    source_path TEXT,
    line_start INTEGER,
    line_end INTEGER,
    speaker TEXT,
    text TEXT,
    excerpt TEXT,
    mpam_axis TEXT,
    pressure_score REAL,
    review_status TEXT DEFAULT 'candidate',
    privacy_status TEXT DEFAULT 'normal',
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS canon_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL,
    event_id TEXT,
    old_status TEXT,
    new_status TEXT,
    reviewer TEXT,
    note TEXT,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS guardian_forecasts (
    id TEXT PRIMARY KEY,
    ts REAL,
    horizon TEXT,
    forecast_text TEXT,
    confidence TEXT,
    evidence_event_ids TEXT,
    action_text TEXT,
    metadata_json TEXT
);
"""

def connect(db_path: Path | str = DEFAULT_DB) -> sqlite3.Connection:
    db_path = Path(db_path).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    return con

def init_db(db_path: Path | str = DEFAULT_DB) -> None:
    con = connect(db_path)
    con.executescript(SCHEMA)
    con.commit()
    con.close()

def upsert_source(source: Dict[str, Any], db_path: Path | str = DEFAULT_DB) -> None:
    init_db(db_path)
    con = connect(db_path)
    con.execute(
        """
        INSERT OR REPLACE INTO sources
        (id,path,url,title,sha256,source_type,created_at,metadata_json)
        VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            source.get("id"),
            source.get("path"),
            source.get("url"),
            source.get("title"),
            source.get("sha256"),
            source.get("source_type"),
            source.get("created_at", time.time()),
            json.dumps(source.get("metadata", {}), ensure_ascii=False),
        ),
    )
    con.commit()
    con.close()

def insert_event(ev: Dict[str, Any], db_path: Path | str = DEFAULT_DB) -> None:
    init_db(db_path)
    con = connect(db_path)
    con.execute(
        """
        INSERT OR REPLACE INTO sensor_events
        (id,ts,event_date,event_type,source_id,source_path,line_start,line_end,speaker,text,excerpt,mpam_axis,pressure_score,review_status,privacy_status,metadata_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            ev.get("id"), ev.get("ts", time.time()), ev.get("date"), ev.get("type"),
            ev.get("source_id"), ev.get("source_file"), ev.get("line_start"), ev.get("line_end"),
            ev.get("speaker"), ev.get("text"), ev.get("excerpt"), ev.get("mpam_axis"),
            ev.get("pressure_score"), ev.get("review_status","candidate"),
            ev.get("privacy_status","normal"),
            json.dumps(ev.get("metadata", {}), ensure_ascii=False),
        ),
    )
    con.commit()
    con.close()

def update_review(event_id: str, new_status: str, reviewer: str = "operator", note: str = "", db_path: Path | str = DEFAULT_DB) -> None:
    init_db(db_path)
    con = connect(db_path)
    row = con.execute("SELECT review_status FROM sensor_events WHERE id=?", (event_id,)).fetchone()
    old = row["review_status"] if row else None
    con.execute("UPDATE sensor_events SET review_status=? WHERE id=?", (new_status, event_id))
    con.execute(
        "INSERT INTO canon_reviews (ts,event_id,old_status,new_status,reviewer,note,metadata_json) VALUES (?,?,?,?,?,?,?)",
        (time.time(), event_id, old, new_status, reviewer, note, "{}"),
    )
    con.commit()
    con.close()

def list_events(status: Optional[str] = None, limit: int = 50, db_path: Path | str = DEFAULT_DB):
    init_db(db_path)
    con = connect(db_path)
    if status:
        rows = con.execute(
            "SELECT * FROM sensor_events WHERE review_status=? ORDER BY ts ASC LIMIT ?",
            (status, limit)
        ).fetchall()
    else:
        rows = con.execute("SELECT * FROM sensor_events ORDER BY ts ASC LIMIT ?", (limit,)).fetchall()
    con.close()
    return [dict(r) for r in rows]

def status_counts(db_path: Path | str = DEFAULT_DB):
    init_db(db_path)
    con = connect(db_path)
    rows = con.execute("SELECT review_status, COUNT(*) AS n FROM sensor_events GROUP BY review_status ORDER BY n DESC").fetchall()
    con.close()
    return {r["review_status"]: r["n"] for r in rows}

def export_events(path: Path | str, statuses=None, db_path: Path | str = DEFAULT_DB):
    init_db(db_path)
    con = connect(db_path)
    if statuses:
        q = ",".join("?" for _ in statuses)
        rows = con.execute(f"SELECT * FROM sensor_events WHERE review_status IN ({q}) ORDER BY ts ASC", list(statuses)).fetchall()
    else:
        rows = con.execute("SELECT * FROM sensor_events ORDER BY ts ASC").fetchall()
    out = Path(path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(dict(r), ensure_ascii=False) + "\n")
    con.close()
