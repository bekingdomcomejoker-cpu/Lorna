from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Any
from .util import now, sha256_text, canonical_json, redact

SCHEMA = r'''
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS sources(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 label TEXT NOT NULL,
 kind TEXT NOT NULL,
 locator TEXT NOT NULL,
 content_sha256 TEXT NOT NULL,
 acquired_at TEXT NOT NULL,
 metadata_json TEXT NOT NULL DEFAULT '{}',
 redacted_preview TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS entities(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 canonical_name TEXT NOT NULL,
 entity_type TEXT NOT NULL DEFAULT 'unknown',
 normalized_key TEXT NOT NULL,
 created_at TEXT NOT NULL,
 UNIQUE(normalized_key, entity_type)
);
CREATE TABLE IF NOT EXISTS entity_aliases(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 entity_id INTEGER NOT NULL,
 alias TEXT NOT NULL,
 source_id INTEGER,
 confidence REAL NOT NULL DEFAULT 0.7,
 FOREIGN KEY(entity_id) REFERENCES entities(id),
 UNIQUE(entity_id, alias)
);
CREATE TABLE IF NOT EXISTS claims(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 source_id INTEGER,
 claim_text TEXT NOT NULL,
 claim_layer TEXT NOT NULL DEFAULT 'factual',
 evidence_grade TEXT NOT NULL DEFAULT 'unverified',
 confidence REAL NOT NULL DEFAULT 0.4,
 status TEXT NOT NULL DEFAULT 'quarantine',
 verification_needed TEXT NOT NULL DEFAULT '',
 risk TEXT NOT NULL DEFAULT 'normal',
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 FOREIGN KEY(source_id) REFERENCES sources(id)
);
CREATE TABLE IF NOT EXISTS claim_entities(
 claim_id INTEGER NOT NULL,
 entity_id INTEGER NOT NULL,
 role TEXT NOT NULL DEFAULT 'mentioned',
 confidence REAL NOT NULL DEFAULT 0.6,
 PRIMARY KEY(claim_id, entity_id, role),
 FOREIGN KEY(claim_id) REFERENCES claims(id),
 FOREIGN KEY(entity_id) REFERENCES entities(id)
);
CREATE TABLE IF NOT EXISTS events(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 claim_id INTEGER,
 event_date TEXT,
 place TEXT,
 event_text TEXT NOT NULL,
 confidence REAL NOT NULL DEFAULT 0.5,
 created_at TEXT NOT NULL,
 FOREIGN KEY(claim_id) REFERENCES claims(id)
);
CREATE TABLE IF NOT EXISTS relations(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 subject_entity_id INTEGER NOT NULL,
 predicate TEXT NOT NULL,
 object_entity_id INTEGER NOT NULL,
 claim_id INTEGER,
 confidence REAL NOT NULL DEFAULT 0.5,
 created_at TEXT NOT NULL,
 FOREIGN KEY(subject_entity_id) REFERENCES entities(id),
 FOREIGN KEY(object_entity_id) REFERENCES entities(id),
 FOREIGN KEY(claim_id) REFERENCES claims(id)
);
CREATE TABLE IF NOT EXISTS verification_tasks(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 claim_id INTEGER,
 task_type TEXT NOT NULL,
 query TEXT NOT NULL,
 target_url TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL DEFAULT 'open',
 result_summary TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 FOREIGN KEY(claim_id) REFERENCES claims(id)
);
CREATE TABLE IF NOT EXISTS chain(
 seq INTEGER PRIMARY KEY AUTOINCREMENT,
 record_type TEXT NOT NULL,
 record_id INTEGER NOT NULL,
 record_hash TEXT NOT NULL,
 prev_hash TEXT NOT NULL,
 chain_hash TEXT NOT NULL,
 created_at TEXT NOT NULL
);
'''

class Ledger:
    def __init__(self, path: str | Path):
        self.path=Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn=sqlite3.connect(self.path)
        self.conn.row_factory=sqlite3.Row
        self.conn.executescript(SCHEMA); self.conn.commit()
    def close(self): self.conn.close()
    def q(self, sql, args=()): return self.conn.execute(sql,args)
    def rows(self, sql, args=()): return [dict(r) for r in self.q(sql,args).fetchall()]
    def last_hash(self):
        r=self.q("SELECT chain_hash FROM chain ORDER BY seq DESC LIMIT 1").fetchone()
        return r[0] if r else "GENESIS"
    def append_chain(self, record_type: str, record_id: int, payload: dict[str,Any]):
        prev=self.last_hash(); rh=sha256_text(canonical_json(payload)); ch=sha256_text(prev+":"+rh)
        self.q("INSERT INTO chain(record_type,record_id,record_hash,prev_hash,chain_hash,created_at) VALUES(?,?,?,?,?,?)",(record_type,record_id,rh,prev,ch,now()))
        self.conn.commit(); return ch
    def add_source(self,label,kind,locator,content_sha256,metadata=None,preview=""):
        cur=self.q("INSERT INTO sources(label,kind,locator,content_sha256,acquired_at,metadata_json,redacted_preview) VALUES(?,?,?,?,?,?,?)",
                   (label,kind,locator,content_sha256,now(),canonical_json(metadata or {}),redact(preview[:2500])))
        sid=cur.lastrowid; self.append_chain("source",sid,{"id":sid,"label":label,"kind":kind,"locator":locator,"sha256":content_sha256}); return sid
    def norm(self,name): return " ".join(name.lower().replace("(pty)","pty").replace("ltd.","ltd").split())
    def upsert_entity(self,name,entity_type="unknown",source_id=None,confidence=0.7):
        key=self.norm(name); created=now()
        self.q("INSERT OR IGNORE INTO entities(canonical_name,entity_type,normalized_key,created_at) VALUES(?,?,?,?)",(name.strip(),entity_type,key,created))
        eid=self.q("SELECT id FROM entities WHERE normalized_key=? AND entity_type=?",(key,entity_type)).fetchone()[0]
        self.q("INSERT OR IGNORE INTO entity_aliases(entity_id,alias,source_id,confidence) VALUES(?,?,?,?)",(eid,name.strip(),source_id,confidence))
        self.conn.commit(); return eid
    def add_claim(self, source_id, claim_text, layer="factual", grade="unverified", confidence=0.4, status="quarantine", verification_needed="", risk="normal"):
        t=now(); cur=self.q("INSERT INTO claims(source_id,claim_text,claim_layer,evidence_grade,confidence,status,verification_needed,risk,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (source_id,claim_text,layer,grade,confidence,status,verification_needed,risk,t,t))
        cid=cur.lastrowid; self.conn.commit(); self.append_chain("claim",cid,{"id":cid,"source_id":source_id,"claim":claim_text,"grade":grade,"confidence":confidence}); return cid
    def link_claim_entity(self,cid,eid,role="mentioned",confidence=0.6):
        self.q("INSERT OR IGNORE INTO claim_entities(claim_id,entity_id,role,confidence) VALUES(?,?,?,?)",(cid,eid,role,confidence)); self.conn.commit()
    def add_event(self,cid,date,place,text,confidence=0.5):
        cur=self.q("INSERT INTO events(claim_id,event_date,place,event_text,confidence,created_at) VALUES(?,?,?,?,?,?)",(cid,date,place,text,confidence,now()))
        eid=cur.lastrowid; self.conn.commit(); self.append_chain("event",eid,{"id":eid,"claim_id":cid,"date":date,"place":place,"text":text}); return eid
    def add_relation(self,s,p,o,cid=None,confidence=0.5):
        cur=self.q("INSERT INTO relations(subject_entity_id,predicate,object_entity_id,claim_id,confidence,created_at) VALUES(?,?,?,?,?,?)",(s,p,o,cid,confidence,now()))
        rid=cur.lastrowid; self.conn.commit(); self.append_chain("relation",rid,{"s":s,"p":p,"o":o,"claim_id":cid}); return rid
    def add_task(self,cid,task_type,query,target_url=""):
        t=now(); cur=self.q("INSERT INTO verification_tasks(claim_id,task_type,query,target_url,created_at,updated_at) VALUES(?,?,?,?,?,?)",(cid,task_type,query,target_url,t,t)); self.conn.commit(); return cur.lastrowid
