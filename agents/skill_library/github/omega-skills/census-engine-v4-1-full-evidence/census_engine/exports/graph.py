from __future__ import annotations
import json
from xml.sax.saxutils import escape
from ..ledger import Ledger
from ..util import write_text

def export_json(db_path,out_path):
    l=Ledger(db_path)
    data={"entities":l.rows('SELECT * FROM entities'),"claims":l.rows('SELECT * FROM claims'),"claim_entities":l.rows('SELECT * FROM claim_entities'),"relations":l.rows('SELECT * FROM relations'),"events":l.rows('SELECT * FROM events')}
    l.close(); write_text(out_path,json.dumps(data,ensure_ascii=False,indent=2)); return out_path

def export_graphml(db_path,out_path):
    l=Ledger(db_path); ents=l.rows('SELECT * FROM entities'); rels=l.rows('SELECT * FROM relations')
    lines=['<?xml version="1.0" encoding="UTF-8"?>','<graphml xmlns="http://graphml.graphdrawing.org/xmlns">','<graph edgedefault="directed">']
    for e in ents: lines.append(f'<node id="e{e["id"]}"><data key="label">{escape(e["canonical_name"])}</data><data key="type">{escape(e["entity_type"])}</data></node>')
    for r in rels: lines.append(f'<edge source="e{r["subject_entity_id"]}" target="e{r["object_entity_id"]}"><data key="predicate">{escape(r["predicate"])}</data></edge>')
    lines += ['</graph>','</graphml>']; l.close(); write_text(out_path,'\n'.join(lines)); return out_path
