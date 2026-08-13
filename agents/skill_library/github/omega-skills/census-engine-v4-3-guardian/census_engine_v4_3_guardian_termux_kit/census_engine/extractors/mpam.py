from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Iterable
from ..util import SA_ID_RE, URL_RE, sa_id_is_valid, sa_id_birthdate

DATE_RES=[re.compile(r"\b(?:20\d{2}|19\d{2})[-/](?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])\b"), re.compile(r"\b(?:0?[1-9]|[12]\d|3[01])[-/](?:0?[1-9]|1[0-2])[-/](?:20\d{2}|19\d{2})\b"), re.compile(r"\b(?:20\d{2}|19\d{2})\b")]
ORG_SUFFIX=r"(?:\(Pty\)\s*Ltd|Pty\s*Ltd|Ltd|NPC|NPO|CC|Inc|Group|Motors|Nissan|Honda|Subaru|Investments|Bank|Finance|Commission|Court)"
ORG_RE=re.compile(r"\b[A-Z][A-Za-z&.'-]*(?:\s+[A-Z][A-Za-z&.'-]*){0,5}\s+"+ORG_SUFFIX+r"\b")
PERSON_RE=re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b")
CASE_RE=re.compile(r"\b(?:RC|CAS|CCMA|GAJB|FSBF|NWKD|ECEL|KZDB|WECT|LP|MP)\s*[-/]?\s*\d{2,8}\s*/\s*\d{2,4}\b", re.I)
PLACE_WORDS={"centurion","midrand","roodepoort","standerton","pretoria","gauteng","benoni","pinetown","farrarmere","heuwel","lenchen","kwazulu-natal","mpumalanga","free state"}
BUCKETS={
 "legal":["court","case","ccma","award","settlement","commission","judgment","saflii","magistrate","docket"],
 "company":["pty","ltd","director","dealership","motus","honda","subaru","nissan","bankfin","franchise","manager","dealer principal"],
 "financial":["fraud","invoice","bank","finance","profit","algorithm","asset","vehicle","floor plan","payout","tender"],
 "surveillance":["grabber","verint","intercept","surveillance","metadata","sensor","osint"],
 "witness":["my ","i saw","i know","he told","she said","my mom","wife","ex wife"],
 "risk":["threat","stolen","towing","narcotics","security","undercover"]
}
@dataclass
class MPAMClaim:
    text:str; date:str=""; place:str=""; persons:list[str]=None; orgs:list[str]=None; cases:list[str]=None; urls:list[str]=None; sa_ids:list[str]=None; bucket:str="general"; confidence:float=0.4

def detect_date(line):
    for r in DATE_RES:
        m=r.search(line)
        if m: return m.group(0)
    return ""

def detect_place(line):
    low=line.lower(); hits=[p.title() for p in PLACE_WORDS if p in low]
    return ", ".join(sorted(hits))

def bucket(line):
    low=line.lower(); scores={k:sum(1 for w in ws if w in low) for k,ws in BUCKETS.items()}
    k=max(scores,key=scores.get); return k if scores[k] else "general"

def extract(text:str)->list[MPAMClaim]:
    out=[]
    for raw in text.splitlines():
        line=" ".join(raw.strip().split())
        if len(line)<20: continue
        persons=[]; orgs=[]
        for o in ORG_RE.findall(line):
            if o not in orgs: orgs.append(o)
        for p in PERSON_RE.findall(line):
            if p.split()[0] in {"The","This","That","What","Node","Source","Evidence","Google","Drive","South","Daily","African"}: continue
            if any(p in o for o in orgs): continue
            if p not in persons: persons.append(p)
        ids=SA_ID_RE.findall(line)
        b=bucket(line); cases=CASE_RE.findall(line); urls=URL_RE.findall(line); date=detect_date(line); place=detect_place(line)
        if b!="general" or date or persons or orgs or cases or urls or ids:
            conf=0.25 + 0.12*bool(date)+0.12*bool(place)+0.12*bool(orgs)+0.08*bool(persons)+0.15*bool(cases)+0.10*bool(urls)
            if ids and all(sa_id_is_valid(x) for x in ids): conf+=0.08
            out.append(MPAMClaim(line,date,place,persons[:8],orgs[:8],cases[:4],urls[:4],ids[:3],b,min(conf,0.95)))
    return out
