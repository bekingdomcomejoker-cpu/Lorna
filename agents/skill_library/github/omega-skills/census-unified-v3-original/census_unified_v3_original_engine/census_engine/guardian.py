from __future__ import annotations
import argparse
import json
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from .entity_resolver import extract_entities
from .ledger import init_db, insert_event
from .mpam import classify_axis, pressure_score
from .source_registry import register_file
from .util import first_date, privacy_status, read_text_lossy, stable_id

def fetch_public_url(url: str, out_dir: Path) -> Path:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only explicit http/https URLs are supported")
    out_dir.mkdir(parents=True, exist_ok=True)
    name = (parsed.netloc + parsed.path).replace("/", "_").strip("_") or "index"
    path = out_dir / f"{name[:120]}.html"
    req = urllib.request.Request(url, headers={"User-Agent": "CensusGuardian/3.0 local source registry"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = r.read(2_000_000)
    path.write_bytes(data)
    return path

def guardian_from_file(path: Path, out_handle):
    init_db()
    src = register_file(path, "guardian_source")
    text = read_text_lossy(path)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # Sensor event is a source-level snapshot + selected signal lines.
    snapshot_text = "\n".join(lines[:20])[:2000]
    ev = {
        "id": stable_id({"guardian": src["id"], "snapshot": snapshot_text}, "gev_"),
        "ts": time.time(),
        "date": first_date(snapshot_text) if first_date(snapshot_text) != "unknown" else first_date(path.name),
        "type": "guardian_sensor",
        "source_id": src["id"],
        "source_file": str(path),
        "line_start": 1,
        "line_end": min(len(lines), 20),
        "speaker": "source_snapshot",
        "text": snapshot_text,
        "excerpt": snapshot_text[:500],
        "entities": extract_entities(snapshot_text),
        "mpam_axis": classify_axis(snapshot_text),
        "pressure_score": pressure_score(snapshot_text),
        "review_status": "candidate",
        "privacy_status": privacy_status(snapshot_text),
        "metadata": {"engine": "omega_guardian_engine.py"},
    }
    insert_event(ev)
    out_handle.write(json.dumps(ev, ensure_ascii=False) + "\n")
    return 1

def iter_input(input_path: Path):
    input_path = Path(input_path).expanduser()
    if input_path.is_file():
        yield input_path
    else:
        for p in input_path.rglob("*"):
            if p.is_file():
                yield p

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="Local folder/file of supplied public/user-owned source material")
    ap.add_argument("--target", action="append", help="Explicit public URL to fetch and register")
    ap.add_argument("--out", default="~/.omega/census/guardian_events.jsonl")
    args = ap.parse_args()

    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    raw_dir = Path("~/.omega/census/guardian_raw").expanduser()
    count = 0

    with out.open("a", encoding="utf-8") as fo:
        if args.input:
            for p in iter_input(Path(args.input)):
                try:
                    count += guardian_from_file(p, fo)
                except Exception as e:
                    print(f"[!] skipped {p}: {e}")
        for url in args.target or []:
            try:
                p = fetch_public_url(url, raw_dir)
                count += guardian_from_file(p, fo)
            except Exception as e:
                print(f"[!] target failed {url}: {e}")

    print(f"[✓] Guardian wrote {count} sensor events to {out}")
