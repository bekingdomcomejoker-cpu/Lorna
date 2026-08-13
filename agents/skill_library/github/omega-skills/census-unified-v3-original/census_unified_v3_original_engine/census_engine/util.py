from __future__ import annotations
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Dict

DATE_RE = re.compile(r"\b(20\d{2}|19\d{2})[-/\.](0?[1-9]|1[0-2])[-/\.](0?[1-9]|[12]\d|3[01])\b")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\d)(?:\+27|0)[ -]?(?:\d[ -]?){8,10}(?!\d)")
SA_ID_RE = re.compile(r"\b\d{13}\b")

def stable_id(obj: Any, prefix: str = "") -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"{prefix}{h[:32]}" if prefix else h[:32]

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_text_lossy(path: Path) -> str:
    data = Path(path).read_bytes()
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(enc)
        except Exception:
            pass
    return data.decode("utf-8", errors="replace")

def first_date(text: str) -> str:
    m = DATE_RE.search(text or "")
    if not m:
        return "unknown"
    y, mo, d = m.groups()
    return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"

def privacy_status(text: str) -> str:
    text = text or ""
    if EMAIL_RE.search(text) or PHONE_RE.search(text) or SA_ID_RE.search(text):
        return "sensitive_candidate"
    return "normal"

def redact(text: str) -> str:
    text = EMAIL_RE.sub("[REDACTED_EMAIL]", text or "")
    text = PHONE_RE.sub("[REDACTED_PHONE]", text)
    text = SA_ID_RE.sub("[REDACTED_ID]", text)
    return text

def now() -> float:
    return time.time()
