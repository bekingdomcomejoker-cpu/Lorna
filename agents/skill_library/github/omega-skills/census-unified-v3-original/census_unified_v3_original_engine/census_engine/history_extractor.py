from __future__ import annotations
import argparse
import json
import re
import time
from pathlib import Path

from .entity_resolver import extract_entities
from .ledger import init_db, insert_event
from .mpam import classify_axis, pressure_score
from .source_registry import register_file
from .util import first_date, privacy_status, read_text_lossy, stable_id

TEXT_EXT = {".txt",".md",".json",".jsonl",".csv",".html",".htm",".mhtml",".log",".xml",".yaml",".yml"}

TYPE_KEYWORDS = {
    "account_access": ["login", "password", "account", "mfa", "subscription", "access"],
    "technical": ["termux", "python", "router", "mikrotik", "script", "zip", "sqlite", "api"],
    "memory_continuity": ["memory", "ledger", "canon", "archive", "checkpoint", "save_memory"],
    "security_forensics": ["security", "forensic", "incident", "evidence", "surveillance", "warning"],
    "relationship_family": ["wife", "mother", "family", "relationship", "home"],
    "household_finance": ["money", "finance", "debt", "bank", "household", "rent"],
    "creative_music": ["song", "lyrics", "music", "guitar", "track"],
    "spiritual_symbolic": ["god", "truth", "spirit", "covenant", "aletheia", "omega"],
}

def classify_type(text: str) -> str:
    low = (text or "").lower()
    scores = {k: sum(1 for w in words if w in low) for k, words in TYPE_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else "general"

def iter_files(root: Path):
    root = Path(root).expanduser()
    if root.is_file():
        yield root
        return
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in TEXT_EXT:
            yield p

def line_candidates(text: str):
    lines = text.splitlines()
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue
        # Prefer lines with dates/identity/source/event pressure; still keep meaningful long lines.
        if len(stripped) > 60 or re.search(r"\b(20\d{2}|19\d{2})\b", stripped):
            yield idx, stripped

def extract(input_path: Path, out: Path):
    init_db()
    out = Path(out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out.open("w", encoding="utf-8") as fo:
        for f in iter_files(input_path):
            try:
                src = register_file(f, "history_source")
                text = read_text_lossy(f)
            except Exception as e:
                continue
            for line_no, line in line_candidates(text):
                ev = {
                    "id": stable_id({"source": src["id"], "line": line_no, "text": line}, "ev_"),
                    "ts": time.time(),
                    "date": first_date(line) if first_date(line) != "unknown" else first_date(f.name),
                    "type": classify_type(line),
                    "source_id": src["id"],
                    "source_file": str(f),
                    "line_start": line_no,
                    "line_end": line_no,
                    "speaker": "document_source",
                    "text": line,
                    "excerpt": line[:500],
                    "entities": extract_entities(line),
                    "mpam_axis": classify_axis(line),
                    "pressure_score": pressure_score(line),
                    "review_status": "candidate",
                    "privacy_status": privacy_status(line),
                    "metadata": {"extractor": "history_extractor.py"},
                }
                insert_event(ev)
                fo.write(json.dumps(ev, ensure_ascii=False) + "\n")
                count += 1
    return count

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", default="~/.omega/census/history_events.jsonl")
    args = ap.parse_args()
    n = extract(Path(args.input).expanduser(), Path(args.out).expanduser())
    print(f"[✓] Extracted {n} candidate events to {Path(args.out).expanduser()}")
