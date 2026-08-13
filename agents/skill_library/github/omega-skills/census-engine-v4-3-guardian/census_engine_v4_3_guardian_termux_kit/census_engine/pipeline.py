from __future__ import annotations
from pathlib import Path
from .ledger import Ledger
from .util import read_text, sha256_text, iter_text_files
from .extractors.mpam import extract
from .evidence import grade

def ingest_text(ledger:Ledger, text:str, label:str, locator:str, kind:str='text'):
    sid=ledger.add_source(label,kind,locator,sha256_text(text),{},text[:2500])
    count=0
    for c in extract(text):
        eg,layer,base_conf,risk,need=grade(c.text,label)
        cid=ledger.add_claim(sid,c.text,layer,eg,max(c.confidence,base_conf),"quarantine",need,risk)
        for org in c.orgs or []:
            eid=ledger.upsert_entity(org,"organization",sid,0.75); ledger.link_claim_entity(cid,eid,"mentioned",0.75)
        for person in c.persons or []:
            eid=ledger.upsert_entity(person,"person",sid,0.65); ledger.link_claim_entity(cid,eid,"mentioned",0.65)
        for case in c.cases or []:
            eid=ledger.upsert_entity(case,"case",sid,0.8); ledger.link_claim_entity(cid,eid,"case_ref",0.8)
        for sa_id in c.sa_ids or []:
            eid=ledger.upsert_entity(f"SA_ID:{sa_id}","identifier",sid,0.9); ledger.link_claim_entity(cid,eid,"identifier",0.9)
        ledger.add_event(cid,c.date,c.place,c.text,c.confidence)
        if c.urls:
            for u in c.urls: ledger.add_task(cid,"fetch_url",u,u)
        elif eg in {"public_record_claim","press_report_claim"}:
            ledger.add_task(cid,"verify_public_record",c.text[:240])
        else:
            ledger.add_task(cid,"source_needed",c.text[:240])
        count+=1
    return sid,count

def ingest_path(db_path:str, path:str):
    ledger=Ledger(db_path); total=0; sources=0
    for f in iter_text_files(path):
        text=read_text(f)
        sid,n=ingest_text(ledger,text,f.name,str(f),'file')
        total+=n; sources+=1
    ledger.close(); return sources,total
