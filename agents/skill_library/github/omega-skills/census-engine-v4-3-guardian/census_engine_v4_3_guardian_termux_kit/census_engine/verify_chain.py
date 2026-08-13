from __future__ import annotations
from .ledger import Ledger
from .util import sha256_text

def verify(db_path:str):
    l=Ledger(db_path); rows=l.rows('SELECT * FROM chain ORDER BY seq'); prev='GENESIS'; bad=[]
    for r in rows:
        expected=sha256_text(prev+':'+r['record_hash'])
        if r['prev_hash']!=prev or r['chain_hash']!=expected: bad.append(r)
        prev=r['chain_hash']
    l.close(); return {"ok":not bad,"records":len(rows),"bad":bad[:10],"tip":prev}
