from __future__ import annotations
import hashlib, json, re, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SA_ID_RE = re.compile(r"\b\d{13}\b")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?27|0)[6-8][0-9][\s.-]?[0-9]{3}[\s.-]?[0-9]{4}(?!\d)")
URL_RE = re.compile(r"https?://[^\s)\]}>\"]+")

def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8", errors="replace"))

def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",",":"))

def read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")

def write_text(path: str | Path, text: str) -> None:
    p=Path(path); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding="utf-8")

def redact(text: str) -> str:
    text = SA_ID_RE.sub("[REDACTED_SA_ID]", text)
    text = PHONE_RE.sub("[REDACTED_PHONE]", text)
    text = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    return text

def sa_id_is_valid(sa_id: str) -> bool:
    if not re.fullmatch(r"\d{13}", sa_id): return False
    digits=[int(c) for c in sa_id]
    odd=sum(digits[0:12:2])
    even_str="".join(str(d) for d in digits[1:12:2])
    even_sum=sum(int(c) for c in str(int(even_str)*2)) if even_str else 0
    check=(10-((odd+even_sum)%10))%10
    return check==digits[-1]

def sa_id_birthdate(sa_id: str) -> str:
    if not re.fullmatch(r"\d{13}", sa_id): return ""
    yy,mm,dd=int(sa_id[:2]), int(sa_id[2:4]), int(sa_id[4:6])
    year=1900+yy if yy > 30 else 2000+yy
    try:
        return datetime(year,mm,dd).date().isoformat()
    except Exception:
        return ""

def iter_text_files(root: str | Path):
    root=Path(root)
    if root.is_file():
        yield root; return
    exts={".txt",".md",".csv",".json",".html",".htm",".xml",".log",".rtf"}
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts and p.stat().st_size < 25_000_000:
            yield p
