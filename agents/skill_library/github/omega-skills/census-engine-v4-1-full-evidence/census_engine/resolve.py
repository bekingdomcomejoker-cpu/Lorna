from __future__ import annotations
from difflib import SequenceMatcher
from .ledger import Ledger

def similarity(a,b): return SequenceMatcher(None,a.lower(),b.lower()).ratio()

def candidates(db_path, threshold=0.84):
    l=Ledger(db_path); ents=l.rows('SELECT id,canonical_name,entity_type,normalized_key FROM entities ORDER BY entity_type, canonical_name'); l.close()
    out=[]
    for i,a in enumerate(ents):
        for b in ents[i+1:]:
            if a['entity_type']!=b['entity_type']: continue
            s=similarity(a['normalized_key'],b['normalized_key'])
            if s>=threshold: out.append({"a":a,"b":b,"similarity":round(s,3)})
    return out
