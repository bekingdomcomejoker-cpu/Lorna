from __future__ import annotations
import csv, json
from pathlib import Path

def read_manual_records(path:str):
    p=Path(path); s=p.read_text(encoding='utf-8',errors='replace')
    if p.suffix.lower()=='.json':
        data=json.loads(s); return data if isinstance(data,list) else [data]
    if p.suffix.lower()=='.csv':
        return list(csv.DictReader(s.splitlines()))
    return [{"text":s,"source_file":str(p)}]
