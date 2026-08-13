from __future__ import annotations
import csv
from pathlib import Path

def load_cipc_csv(path:str):
    with open(path,newline='',encoding='utf-8-sig',errors='replace') as f:
        return list(csv.DictReader(f))

def find_company(rows, query:str):
    q=query.lower()
    return [r for r in rows if q in ' '.join(str(v).lower() for v in r.values())]
