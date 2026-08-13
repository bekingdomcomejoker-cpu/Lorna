from __future__ import annotations
from pathlib import Path
from ..ledger import Ledger
from ..util import now, write_text, redact

def md_escape(s): return str(s or '').replace('|','\\|').replace('\n',' ')

def make_report(db_path:str, out_path:str, redact_pii=True):
    l=Ledger(db_path)
    sources=l.rows('SELECT * FROM sources ORDER BY id')
    claims=l.rows('''SELECT c.*, group_concat(e.canonical_name, '; ') AS entities FROM claims c
        LEFT JOIN claim_entities ce ON ce.claim_id=c.id LEFT JOIN entities e ON e.id=ce.entity_id GROUP BY c.id ORDER BY c.id''')
    events=l.rows('SELECT * FROM events ORDER BY event_date, id')
    tasks=l.rows('SELECT * FROM verification_tasks ORDER BY status, id')
    chain=l.rows('SELECT chain_hash FROM chain ORDER BY seq DESC LIMIT 1')
    lines=[f"# Census Engine v4.1 Evidence Report", "", f"Generated: {now()}", "", "## Source Boundary", "This report preserves sources, claims, evidence grades, events, and verification tasks. It does not treat unverified claims as proven.", "", "## Sources"]
    for s in sources: lines.append(f"- #{s['id']} **{md_escape(s['label'])}** — {s['kind']} — `{s['content_sha256'][:16]}…` — {md_escape(s['locator'])}")
    lines += ["", "## Claim Ledger", "| ID | Entities | Grade | Status | Risk | Confidence | Claim | Verification Needed |", "|---:|---|---|---|---|---:|---|---|"]
    for c in claims:
        txt=redact(c['claim_text']) if redact_pii else c['claim_text']
        lines.append(f"| {c['id']} | {md_escape(c['entities'])} | {c['evidence_grade']} | {c['status']} | {c['risk']} | {c['confidence']:.2f} | {md_escape(txt)} | {md_escape(c['verification_needed'])} |")
    lines += ["", "## Event Candidates", "| ID | Claim | Date | Place | Confidence | Event |", "|---:|---:|---|---|---:|---|"]
    for e in events:
        txt=redact(e['event_text']) if redact_pii else e['event_text']
        lines.append(f"| {e['id']} | {e['claim_id']} | {md_escape(e['event_date'])} | {md_escape(e['place'])} | {e['confidence']:.2f} | {md_escape(txt)} |")
    lines += ["", "## Verification Tasks", "| ID | Claim | Type | Status | Query/Target | Result |", "|---:|---:|---|---|---|---|"]
    for t in tasks: lines.append(f"| {t['id']} | {t['claim_id']} | {t['task_type']} | {t['status']} | {md_escape(t['query'] or t['target_url'])} | {md_escape(t['result_summary'])} |")
    lines += ["", "## Chain Tip", f"`{chain[0]['chain_hash'] if chain else 'GENESIS'}`"]
    l.close(); write_text(out_path,"\n".join(lines)); return out_path
