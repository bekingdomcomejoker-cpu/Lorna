from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional

from .engine import BUCKET_FILES, DEFAULT_DATA_DIR, iter_jsonl

DEFAULT_REVIEW_STATE = Path(os.environ.get("CENSUS_REVIEW_STATE", "out/review_decisions.jsonl"))
VALID_DECISIONS = {"canon", "witness", "reject", "private", "skip"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def stable_record_id(obj: dict) -> str:
    """Return the best available stable ID for a CENSUS record."""
    for key in ("original_event_id", "v3_event_id", "event_id", "id", "duplicate_fingerprint"):
        val = obj.get(key)
        if val:
            return str(val)
    payload = json.dumps({
        "text": obj.get("text", ""),
        "source": obj.get("source_file_resolved") or obj.get("source_file_original") or obj.get("source_path_v4"),
        "line": obj.get("source_line_citation_v5") or obj.get("source_line_start_v4"),
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def short(text: Optional[str], max_len: int = 500) -> str:
    text = (text or "").replace("\r", " ").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len-3] + "..."


def load_decisions(path: Path) -> Dict[str, dict]:
    latest: Dict[str, dict] = {}
    if not path.exists():
        return latest
    for obj in iter_jsonl(path):
        rid = obj.get("record_id")
        if rid:
            latest[str(rid)] = obj
    return latest


def append_decision(path: Path, decision: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(decision, ensure_ascii=False, sort_keys=True) + "\n")


def iter_bucket_records(data_dir: Path, bucket: str) -> Iterator[dict]:
    if bucket not in BUCKET_FILES:
        raise KeyError(f"Unknown bucket {bucket!r}; choose one of: {', '.join(BUCKET_FILES)}")
    path = data_dir / BUCKET_FILES[bucket]
    if not path.exists():
        raise FileNotFoundError(path)
    yield from iter_jsonl(path)


def render_record(obj: dict, bucket: str, index: int, total: Optional[int], existing: Optional[dict]) -> str:
    rid = stable_record_id(obj)
    title = f"=== CENSUS HUMAN REVIEW | {bucket} | {index}"
    if total is not None:
        title += f"/{total}"
    title += " ==="
    lines = [title]
    if existing:
        lines.append(f"Existing decision: {existing.get('decision')} | {existing.get('decided_at')} | {existing.get('note','')}")
    lines += [
        f"Record ID:     {rid}",
        f"Tier:          {obj.get('promotion_tier_v5') or obj.get('canon_strength_v5') or bucket}",
        f"Date:          {obj.get('event_date_v5') or obj.get('event_date') or 'unknown'}",
        f"Date strength: {obj.get('date_lock_strength_v5') or obj.get('event_date_provenance_v5') or 'unknown'}",
        f"Type:          {obj.get('event_type_v2') or obj.get('event_type') or 'unknown'}",
        f"Speaker:       {obj.get('speaker_role_v4') or obj.get('speaker_role_guess') or 'unknown'}",
        f"Citation:      {obj.get('source_line_citation_v5') or obj.get('source_line_start_v4') or 'missing'}",
        f"Source:        {Path(str(obj.get('source_file_original') or obj.get('source_path_v4') or obj.get('source_file_resolved') or '')).name}",
        "-" * 72,
        short(obj.get("text"), 1400),
    ]
    excerpt = obj.get("source_evidence_excerpt")
    if excerpt and excerpt != obj.get("text"):
        lines += ["-" * 72, "Source excerpt:", short(excerpt, 900)]
    lines += ["-" * 72]
    return "\n".join(lines)


def decision_payload(obj: dict, bucket: str, decision: str, note: str = "", reviewer: str = "local_operator") -> dict:
    rid = stable_record_id(obj)
    return {
        "record_id": rid,
        "decision": decision,
        "note": note,
        "reviewer": reviewer,
        "decided_at": utc_now(),
        "bucket": bucket,
        "source_line_citation_v5": obj.get("source_line_citation_v5"),
        "event_date_v5": obj.get("event_date_v5"),
        "event_type_v2": obj.get("event_type_v2"),
        "speaker_role_v4": obj.get("speaker_role_v4"),
        "text_sha256": hashlib.sha256((obj.get("text") or "").encode("utf-8")).hexdigest(),
    }


def apply_decisions(data_dir: Path, state_path: Path, include_decisions: Iterable[str]) -> List[dict]:
    latest = load_decisions(state_path)
    wanted = set(include_decisions)
    out: List[dict] = []
    for bucket in BUCKET_FILES:
        for obj in iter_bucket_records(data_dir, bucket):
            rid = stable_record_id(obj)
            dec = latest.get(rid)
            if not dec:
                continue
            if dec.get("decision") not in wanted:
                continue
            new = dict(obj)
            new["human_review_decision"] = dec.get("decision")
            new["human_review_note"] = dec.get("note", "")
            new["human_review_decided_at"] = dec.get("decided_at")
            new["human_review_reviewer"] = dec.get("reviewer")
            out.append(new)
    return out


def write_jsonl(path: Path, records: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for obj in records:
            f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def review_interactive(
    bucket: str = "canon_core",
    data_dir: Path = DEFAULT_DATA_DIR,
    state_path: Path = DEFAULT_REVIEW_STATE,
    reviewer: str = "local_operator",
    limit: Optional[int] = None,
    offset: int = 0,
) -> None:
    records = list(iter_bucket_records(data_dir, bucket))
    latest = load_decisions(state_path)
    total = len(records)
    changed = 0
    seen = 0
    for i, obj in enumerate(records, start=1):
        if i <= offset:
            continue
        rid = stable_record_id(obj)
        if latest.get(rid, {}).get("decision") in {"canon", "witness", "reject", "private"}:
            continue
        seen += 1
        if limit is not None and seen > limit:
            break
        os.system("clear")
        print(render_record(obj, bucket, i, total, latest.get(rid)))
        print("[c] canon  [w] witness  [r] reject  [p] private  [s] skip  [q] save & quit")
        choice = input("Decision: ").strip().lower()[:1]
        if choice == "q":
            break
        mapping = {"c": "canon", "w": "witness", "r": "reject", "p": "private", "s": "skip"}
        decision = mapping.get(choice, "skip")
        note = ""
        if decision in {"canon", "witness", "reject", "private"}:
            note = input("Optional note: ").strip()
        payload = decision_payload(obj, bucket, decision, note=note, reviewer=reviewer)
        append_decision(state_path, payload)
        latest[rid] = payload
        if decision != "skip":
            changed += 1
    print(f"\n[+] Review complete. Saved {changed} non-skip decisions to {state_path}")


def review_status(data_dir: Path = DEFAULT_DATA_DIR, state_path: Path = DEFAULT_REVIEW_STATE) -> dict:
    latest = load_decisions(state_path)
    counts = {"canon": 0, "witness": 0, "reject": 0, "private": 0, "skip": 0, "unreviewed_loaded_buckets": 0}
    reviewed_ids = set(latest)
    loaded_ids = set()
    for bucket in BUCKET_FILES:
        for obj in iter_bucket_records(data_dir, bucket):
            rid = stable_record_id(obj)
            loaded_ids.add(rid)
    for dec in latest.values():
        d = dec.get("decision")
        counts[d] = counts.get(d, 0) + 1
    counts["loaded_records"] = len(loaded_ids)
    counts["decisions_total"] = len(reviewed_ids)
    counts["unreviewed_loaded_buckets"] = len(loaded_ids - reviewed_ids)
    counts["state_path"] = str(state_path)
    counts["data_dir"] = str(data_dir)
    return counts


def export_reviewed(data_dir: Path, state_path: Path, out_path: Path, include: str = "canon") -> int:
    wanted = [x.strip() for x in include.split(",") if x.strip()]
    if not wanted:
        wanted = ["canon"]
    records = apply_decisions(data_dir, state_path, wanted)
    return write_jsonl(out_path, records)
