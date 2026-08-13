from __future__ import annotations
from ..ledger import Ledger

def review(db_path):
    l=Ledger(db_path)
    rows=l.rows("SELECT id,claim_text,evidence_grade,status FROM claims WHERE status='quarantine' ORDER BY id")
    for r in rows:
        print(f"\n#{r['id']} [{r['evidence_grade']}] {r['claim_text']}")
        ans=input("mark [c]anon [w]itness [r]ejected [enter skip]: ").strip().lower()
        if ans in {'c','w','r'}:
            status={'c':'canon','w':'witness','r':'rejected'}[ans]
            l.q("UPDATE claims SET status=?, updated_at=datetime('now') WHERE id=?",(status,r['id'])); l.conn.commit()
    l.close()
