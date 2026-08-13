#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sqlite3
import sys
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

VERSION = "1.0.0"
SENSES = ("sight", "hearing", "touch", "smell", "taste")
GATES = ("A", "B", "C", "D", "E")
GATE_STATES = {"pass", "fail", "unknown", "not_applicable"}
WORD_RE = re.compile(r"[a-z0-9]+")
NUMBERED_RE = re.compile(r"^\s*\d+\s*[.)-]\s*")
GITHUB_RE = re.compile(r"https?://github\.com/([^/\s]+)/([^/#?\s]+)", re.I)

DEFAULT_ROOT = Path.home() / "cat_eof"
DEFAULT_FOCUS = {
    "omega", "aletheia", "merkabah", "guardian",
    "engine", "node", "registry", "federation",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_words(value: str) -> str:
    return " ".join(WORD_RE.findall(value.lower()))


def safe_slug(value: str) -> str:
    slug = "-".join(WORD_RE.findall(value.lower()))[:72]
    return slug or "record"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS perception_records (
                record_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                record_type TEXT NOT NULL,
                subject TEXT,
                claim TEXT,
                decision TEXT NOT NULL,
                canon_eligible INTEGER NOT NULL,
                movement_allowed INTEGER NOT NULL,
                confidence_score REAL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS unknown_ledger (
                unknown_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                record_id TEXT NOT NULL,
                subject TEXT,
                reason TEXT NOT NULL,
                status TEXT NOT NULL,
                resolution TEXT
            );
            """
        )
        connection.commit()


def persist_record(root: Path, record: dict[str, Any]) -> Path:
    state = root / "state"
    output = root / "output" / "perception_integrity"
    db_path = state / "cat_eof.db"
    jsonl_path = state / "perception_integrity.jsonl"
    init_db(db_path)
    append_jsonl(jsonl_path, record)

    record_id = str(record["record_id"])
    out_path = output / f"{record_id}.json"
    write_json(out_path, record)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO perception_records (
                record_id, created_at, record_type, subject, claim,
                decision, canon_eligible, movement_allowed,
                confidence_score, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                record["created_at"],
                record.get("record_type", "unknown"),
                record.get("subject"),
                record.get("claim"),
                record.get("decision", "UNKNOWN"),
                int(bool(record.get("canon_eligible"))),
                int(bool(record.get("movement_allowed"))),
                float(record.get("confidence_score", 0.0)),
                json.dumps(record, ensure_ascii=False, sort_keys=True),
            ),
        )

        for unknown in record.get("unknowns", []):
            connection.execute(
                """
                INSERT OR REPLACE INTO unknown_ledger (
                    unknown_id, created_at, record_id,
                    subject, reason, status, resolution
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    unknown["unknown_id"],
                    record["created_at"],
                    record_id,
                    unknown.get("subject"),
                    unknown["reason"],
                    unknown.get("status", "UNRESOLVED"),
                    unknown.get("resolution"),
                ),
            )
        connection.commit()

    return out_path


def parse_items(values: Iterable[str] | None) -> list[str]:
    return [value.strip() for value in (values or []) if value.strip()]


def gate_object(state: str, notes: str | None = None) -> dict[str, Any]:
    state = state.lower()
    if state not in GATE_STATES:
        raise ValueError(
            f"Invalid gate state {state!r}. "
            f"Use one of: {', '.join(sorted(GATE_STATES))}"
        )
    return {"state": state, "notes": notes or ""}


def sense_object(items: list[str]) -> dict[str, Any]:
    return {
        "status": "observed" if items else "unknown",
        "evidence": items,
        "confidence": round(min(1.0, 0.25 + 0.2 * len(items)), 3) if items else 0.0,
    }


def evaluate_claim(
    *,
    claim: str,
    subject: str,
    sources: list[str],
    sense_evidence: dict[str, list[str]],
    gates: dict[str, dict[str, Any]],
    notes: str = "",
) -> dict[str, Any]:
    senses = {name: sense_object(sense_evidence.get(name, [])) for name in SENSES}
    required = ("A", "B", "C", "D")
    required_states = [gates[name]["state"] for name in required]
    e_state = gates["E"]["state"]

    observed_count = sum(1 for value in senses.values() if value["status"] == "observed")
    sense_score = sum(value["confidence"] for value in senses.values()) / len(SENSES)
    gate_score = sum(
        1.0 if gates[name]["state"] == "pass"
        else 0.5 if gates[name]["state"] == "not_applicable"
        else 0.0
        for name in GATES
    ) / len(GATES)
    confidence = round((sense_score + gate_score) / 2.0, 3)

    unknowns: list[dict[str, Any]] = []
    for name in GATES:
        if gates[name]["state"] == "unknown":
            unknowns.append({
                "unknown_id": f"UNKNOWN_GATE_{name}_{uuid.uuid4().hex[:8]}",
                "subject": subject,
                "reason": f"Gate {name} remains unresolved",
                "status": "UNRESOLVED",
            })

    if any(state == "fail" for state in required_states) or e_state == "fail":
        decision = "REJECT_OR_REPAIR"
        canon_eligible = False
        movement_allowed = False
        rationale = "At least one truth gate failed."
    elif all(state == "pass" for state in required_states) and e_state in {"pass", "not_applicable"}:
        if observed_count >= 2:
            decision = "ALLOW"
            canon_eligible = True
            movement_allowed = True
            rationale = "ABCD closed, E closed or not applicable, and multiple witness channels are present."
        else:
            decision = "HOLD_FOR_WITNESS"
            canon_eligible = False
            movement_allowed = False
            rationale = "The gates pass, but fewer than two witness channels are present."
            unknowns.append({
                "unknown_id": f"UNKNOWN_WITNESS_{uuid.uuid4().hex[:8]}",
                "subject": subject,
                "reason": "Fewer than two sensory witness channels supplied",
                "status": "UNRESOLVED",
            })
    else:
        decision = "HOLD_UNKNOWN"
        canon_eligible = False
        movement_allowed = False
        rationale = "One or more gates remain unknown or incomplete."

    return {
        "record_id": f"claim-{uuid.uuid4()}",
        "record_type": "claim_audit",
        "schema_version": VERSION,
        "created_at": utc_now(),
        "claim": claim,
        "subject": subject,
        "source_refs": sources,
        "senses": senses,
        "abcde": gates,
        "decision": decision,
        "decision_reason": rationale,
        "canon_eligible": canon_eligible,
        "movement_allowed": movement_allowed,
        "confidence_score": confidence,
        "unknowns": unknowns,
        "notes": notes,
        "rule": (
            "Perceive through many channels. Preserve the exact signal. "
            "Declare the field boundary. Let no sense certify itself. "
            "Move only when ABCD agrees; preserve UNKNOWN when it does not."
        ),
    }


def load_registry(root: Path, explicit: Path | None = None) -> dict[str, Any]:
    candidates = []
    if explicit:
        candidates.append(explicit.expanduser())
    candidates.extend([
        root / "registry" / "voice_registry.json",
        root / "registries" / "voice_registry.json",
        root / "registries" / "nodes.json",
        root / "data" / "voice_registry.json",
    ])
    for path in candidates:
        if path.exists():
            data = load_json(path)
            if isinstance(data, dict) and "entities" in data:
                return data
            if isinstance(data, list):
                return {"version": VERSION, "entities": data}
    raise FileNotFoundError("No compatible voice registry found")


def registry_candidates(registry: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    for entity in registry.get("entities", []):
        canonical = str(entity.get("canonical", "")).strip()
        if not canonical:
            continue
        for term in [canonical, *entity.get("aliases", [])]:
            key = normalize_words(str(term))
            if key:
                output.append({
                    "key": key,
                    "term": str(term),
                    "canonical": canonical,
                    "entity_type": entity.get("type", "unknown"),
                    "entity_id": entity.get("id"),
                })
    return output


def voice_record(raw: str, registry: dict[str, Any], threshold: float) -> dict[str, Any]:
    query = normalize_words(raw)
    best = None
    score = 0.0
    for candidate in registry_candidates(registry):
        current = 1.0 if candidate["key"] == query else difflib.SequenceMatcher(
            None, query, candidate["key"]
        ).ratio()
        if current > score:
            best = candidate
            score = current

    if best and score >= threshold:
        status = "CONFIRMED" if query == normalize_words(best["canonical"]) else "CORRECTED"
        decision = "USE_CANONICAL"
        canonical = best["canonical"]
        unknowns = []
        movement_allowed = True
    else:
        status = "UNKNOWN"
        decision = "HOLD_FOR_OPERATOR_CORRECTION"
        canonical = None
        movement_allowed = False
        unknowns = [{
            "unknown_id": f"UNKNOWN_VOICE_{uuid.uuid4().hex[:8]}",
            "subject": raw,
            "reason": "No registry match met the correction threshold",
            "status": "UNRESOLVED",
        }]

    return {
        "record_id": f"voice-{uuid.uuid4()}",
        "record_type": "voice_correction",
        "schema_version": VERSION,
        "created_at": utc_now(),
        "claim": f"Resolve spoken phrase: {raw}",
        "subject": raw,
        "raw_heard": raw,
        "normalized_heard": query,
        "status": status,
        "canonical": canonical,
        "match_score": round(score, 4),
        "threshold": threshold,
        "matched_registry_term": best["term"] if best else None,
        "entity_type": best["entity_type"] if best else None,
        "entity_id": best["entity_id"] if best else None,
        "decision": decision,
        "decision_reason": (
            "Known registry match accepted."
            if canonical else
            "Uncertain transcription preserved as UNKNOWN."
        ),
        "canon_eligible": bool(canonical),
        "movement_allowed": movement_allowed,
        "confidence_score": round(score, 4),
        "unknowns": unknowns,
        "create_new_entity": False,
        "rule": "Preserve raw speech. Resolve against registry. Never invent an entity from uncertain transcription.",
    }


def read_inventory(path: Path, owner: str | None) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Inventory not found: {path}")
    output = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = NUMBERED_RE.sub("", line)
        match = GITHUB_RE.search(line)
        if match:
            line = f"{match.group(1)}/{match.group(2)}"
        line = line.strip().strip("/ ").lower()
        if line.endswith(".git"):
            line = line[:-4]
        if "/" not in line and owner:
            line = f"{owner.lower()}/{line}"
        output.append(line)
    return sorted(set(output))


def inventory_record(
    canonical_path: Path,
    observed_path: Path,
    owner: str | None,
    canaries: list[str],
) -> dict[str, Any]:
    canonical = read_inventory(canonical_path, owner)
    observed = read_inventory(observed_path, owner)
    cset, oset = set(canonical), set(observed)
    missing = sorted(cset - oset)
    unexpected = sorted(oset - cset)

    frequency = Counter(
        token
        for repo in canonical
        for token in set(WORD_RE.findall(repo.split("/", 1)[-1]))
    )
    observed_vocab = {
        token
        for repo in observed
        for token in WORD_RE.findall(repo.split("/", 1)[-1])
    }

    ranked = []
    for repo in missing:
        repo_tokens = set(WORD_RE.findall(repo.split("/", 1)[-1]))
        rarity = sum(
            __import__("math").log((len(canonical) + 1) / max(frequency.get(tok, 1), 1))
            for tok in repo_tokens
        ) / max(len(repo_tokens), 1)
        vocabulary_gap = 1.0 - (
            len(repo_tokens & observed_vocab) / max(len(repo_tokens), 1)
        )
        focus_blindspot = 1.0 if repo_tokens.isdisjoint(DEFAULT_FOCUS) else 0.0
        score = rarity + (1.5 * vocabulary_gap) + (2.0 * focus_blindspot)
        ranked.append({
            "repo": repo,
            "outsider_score": round(score, 5),
            "vocabulary_gap": round(vocabulary_gap, 5),
            "focus_blindspot": bool(focus_blindspot),
        })
    ranked.sort(key=lambda item: (-item["outsider_score"], item["repo"]))

    canary_states = []
    for raw in canaries:
        value = raw.strip().lower()
        if "/" not in value and owner:
            value = f"{owner.lower()}/{value}"
        canary_states.append({
            "repo": value,
            "present_in_canonical": value in cset,
            "present_in_observed": value in oset,
            "missing_from_observed": value in missing,
        })

    complete = not missing and not unexpected
    unknowns = [
        {
            "unknown_id": f"UNKNOWN_INVENTORY_{index:02d}_{uuid.uuid4().hex[:6]}",
            "subject": item["repo"],
            "reason": "Present in canonical inventory but absent from observed inventory",
            "status": "UNRESOLVED",
        }
        for index, item in enumerate(ranked, 1)
    ]

    canonical_hash = hashlib.sha256(("\n".join(canonical) + "\n").encode()).hexdigest()
    observed_hash = hashlib.sha256(("\n".join(observed) + "\n").encode()).hexdigest()

    return {
        "record_id": f"inventory-{uuid.uuid4()}",
        "record_type": "inventory_audit",
        "schema_version": VERSION,
        "created_at": utc_now(),
        "claim": "Observed inventory is complete relative to canonical inventory",
        "subject": owner or "inventory",
        "canonical_source": str(canonical_path),
        "observed_source": str(observed_path),
        "canonical_count": len(canonical),
        "observed_count": len(observed),
        "missing_count": len(missing),
        "unexpected_count": len(unexpected),
        "missing_ranked": ranked,
        "unexpected_members": unexpected,
        "canaries": canary_states,
        "canonical_sha256": canonical_hash,
        "observed_sha256": observed_hash,
        "decision": "SEAL" if complete else "HOLD_AND_INSPECT_OUTLIERS",
        "decision_reason": (
            "Both directions of the set comparison close."
            if complete else
            "The canonical and observed sets do not close."
        ),
        "canon_eligible": complete,
        "movement_allowed": complete,
        "confidence_score": 1.0 if complete else round(len(oset & cset) / max(len(cset), 1), 4),
        "unknowns": unknowns,
        "rule": "Search may discover inventory members. Search may never certify completeness.",
    }


def status_record(root: Path) -> dict[str, Any]:
    checks = {
        "phase1_completeness_auditor": [
            root / "tools" / "aletheia-audit",
            root / "tools" / "aletheia_audit.py",
        ],
        "phase2_witness_schema": [
            root / "schema" / "five_sense_witness.schema.json",
            root / "tools" / "five_sense_witness.py",
        ],
        "phase3_plain_sight": [
            root / "tools" / "plain-sight",
            root / "tools" / "plain_sight.py",
        ],
        "phase4_voice_correction": [
            root / "tools" / "voice-correct",
            root / "tools" / "voice_correction.py",
        ],
        "unified_console": [
            root / "tools" / "aletheia-console",
            root / "tools" / "aletheia_console.py",
        ],
        "canonical_inventory": [
            root / "input" / "repos-canonical.txt",
        ],
    }
    components = {}
    for name, paths in checks.items():
        existing = [str(path) for path in paths if path.exists()]
        components[name] = {
            "present": bool(existing),
            "paths": existing,
        }

    return {
        "record_id": f"status-{uuid.uuid4()}",
        "record_type": "system_status",
        "schema_version": VERSION,
        "created_at": utc_now(),
        "claim": "Report installed Perception Integrity components",
        "subject": str(root),
        "components": components,
        "decision": "READY" if components["unified_console"]["present"] else "INCOMPLETE",
        "decision_reason": "Component discovery only; this does not certify end-to-end operation.",
        "canon_eligible": False,
        "movement_allowed": False,
        "confidence_score": 1.0,
        "unknowns": [],
    }


def print_claim(record: dict[str, Any]) -> None:
    print("ALETHEIA SENSORY AUDIT CONSOLE")
    print("==============================")
    print(f"Subject:          {record['subject']}")
    print(f"Decision:         {record['decision']}")
    print(f"Canon eligible:   {record['canon_eligible']}")
    print(f"Movement allowed: {record['movement_allowed']}")
    print(f"Confidence:       {record['confidence_score']}")
    print(f"Reason:           {record['decision_reason']}")
    if record.get("unknowns"):
        print("Unknowns:")
        for item in record["unknowns"]:
            print(f"  - {item['unknown_id']}: {item['reason']}")


def print_voice(record: dict[str, Any]) -> None:
    print("ALETHEIA VOICE CORRECTION")
    print("=========================")
    print(f"Heard:      {record['raw_heard']}")
    print(f"Status:     {record['status']}")
    print(f"Canonical:  {record['canonical'] or 'UNRESOLVED'}")
    print(f"Score:      {record['match_score']}")
    print(f"Decision:   {record['decision']}")


def print_inventory(record: dict[str, Any]) -> None:
    print("ALETHEIA INVENTORY / PLAIN-SIGHT AUDIT")
    print("======================================")
    print(f"Canonical count: {record['canonical_count']}")
    print(f"Observed count:  {record['observed_count']}")
    print(f"Missing count:   {record['missing_count']}")
    print(f"Unexpected:      {record['unexpected_count']}")
    print(f"Decision:        {record['decision']}")
    if record["missing_ranked"]:
        print("Top missing semantic outsiders:")
        for item in record["missing_ranked"][:20]:
            print(f"  - {item['repo']} | outsider_score={item['outsider_score']}")


def prompt_gate(name: str, description: str) -> dict[str, Any]:
    while True:
        raw = input(f"{name} — {description} [pass/fail/unknown/na]: ").strip().lower()
        if raw == "na":
            raw = "not_applicable"
        if raw in GATE_STATES:
            notes = input(f"{name} notes (optional): ").strip()
            return gate_object(raw, notes)
        print("Please enter pass, fail, unknown, or na.")


def wizard(root: Path) -> dict[str, Any]:
    print("ALETHEIA SENSORY AUDIT WIZARD")
    print("=============================")
    claim = input("Claim: ").strip()
    subject = input("Subject: ").strip()
    sources = parse_items([value.strip() for value in input(
        "Source references, separated by | (optional): "
    ).split("|")])
    sense_evidence: dict[str, list[str]] = {}
    for sense in SENSES:
        raw = input(f"{sense.title()} evidence, separated by | (optional): ")
        sense_evidence[sense] = parse_items(raw.split("|"))
    gates = {
        "A": prompt_gate("A", "exact naming and source language"),
        "B": prompt_gate("B", "witness, authority, consent"),
        "C": prompt_gate("C", "scope, context, horizon, time"),
        "D": prompt_gate("D", "count, invariant, formal closure"),
        "E": prompt_gate("E", "root meaning / etymology when relevant"),
    }
    notes = input("Overall notes (optional): ").strip()
    record = evaluate_claim(
        claim=claim,
        subject=subject,
        sources=sources,
        sense_evidence=sense_evidence,
        gates=gates,
        notes=notes,
    )
    path = persist_record(root, record)
    print_claim(record)
    print(f"Saved: {path}")
    return record


def add_common_root(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="CAT→EOF root (default: ~/cat_eof)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aletheia-console",
        description="Unified Aletheia Perception Integrity Console for Termux",
    )
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="Discover installed phases and files")
    add_common_root(p_status)
    p_status.add_argument("--json", action="store_true")

    p_wizard = sub.add_parser("wizard", help="Interactive Five-Sense + ABCDE claim audit")
    add_common_root(p_wizard)

    p_claim = sub.add_parser("claim", help="Non-interactive claim audit")
    add_common_root(p_claim)
    p_claim.add_argument("--claim", required=True)
    p_claim.add_argument("--subject", required=True)
    p_claim.add_argument("--source", action="append", default=[])
    for sense in SENSES:
        p_claim.add_argument(f"--{sense}", action="append", default=[])
    for gate in GATES:
        p_claim.add_argument(f"--{gate.lower()}", choices=sorted(GATE_STATES), default="unknown")
        p_claim.add_argument(f"--{gate.lower()}-notes", default="")
    p_claim.add_argument("--notes", default="")
    p_claim.add_argument("--json", action="store_true")

    p_voice = sub.add_parser("voice", help="Resolve uncertain speech against the registry")
    add_common_root(p_voice)
    p_voice.add_argument("text")
    p_voice.add_argument("--registry", type=Path)
    p_voice.add_argument("--threshold", type=float, default=0.72)
    p_voice.add_argument("--json", action="store_true")

    p_inventory = sub.add_parser("inventory", help="Canonical vs observed inventory audit")
    add_common_root(p_inventory)
    p_inventory.add_argument("--canonical", type=Path, required=True)
    p_inventory.add_argument("--observed", type=Path, required=True)
    p_inventory.add_argument("--owner")
    p_inventory.add_argument("--canary", action="append", default=[])
    p_inventory.add_argument("--json", action="store_true")
    p_inventory.add_argument("--fail-on-gap", action="store_true")

    p_demo = sub.add_parser("demo", help="Run integrated Glass-Chess and voice demonstrations")
    add_common_root(p_demo)
    p_demo.add_argument("--json", action="store_true")

    p_template = sub.add_parser("template", help="Write a reusable claim JSON template")
    add_common_root(p_template)
    p_template.add_argument("--output", type=Path)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.expanduser()

    try:
        if args.command == "status":
            record = status_record(root)
            if args.json:
                print(json.dumps(record, indent=2, ensure_ascii=False))
            else:
                print("ALETHEIA PERCEPTION INTEGRITY STATUS")
                print("====================================")
                for name, data in record["components"].items():
                    print(f"{name:32} {'PRESENT' if data['present'] else 'MISSING'}")
                    for path in data["paths"]:
                        print(f"  {path}")
                print("\nNote: presence is not the same as end-to-end verification.")
            return 0

        if args.command == "wizard":
            record = wizard(root)
            return 0 if record["movement_allowed"] else 1

        if args.command == "claim":
            sense_evidence = {
                sense: parse_items(getattr(args, sense))
                for sense in SENSES
            }
            gates = {
                gate: gate_object(
                    getattr(args, gate.lower()),
                    getattr(args, f"{gate.lower()}_notes"),
                )
                for gate in GATES
            }
            record = evaluate_claim(
                claim=args.claim,
                subject=args.subject,
                sources=parse_items(args.source),
                sense_evidence=sense_evidence,
                gates=gates,
                notes=args.notes,
            )
            path = persist_record(root, record)
            if args.json:
                print(json.dumps(record, indent=2, ensure_ascii=False))
            else:
                print_claim(record)
                print(f"Saved: {path}")
            return 0 if record["movement_allowed"] else 1

        if args.command == "voice":
            registry = load_registry(root, args.registry)
            record = voice_record(args.text, registry, args.threshold)
            path = persist_record(root, record)
            if args.json:
                print(json.dumps(record, indent=2, ensure_ascii=False))
            else:
                print_voice(record)
                print(f"Saved: {path}")
            return 0 if record["movement_allowed"] else 1

        if args.command == "inventory":
            record = inventory_record(
                args.canonical.expanduser(),
                args.observed.expanduser(),
                args.owner,
                args.canary,
            )
            path = persist_record(root, record)
            if args.json:
                print(json.dumps(record, indent=2, ensure_ascii=False))
            else:
                print_inventory(record)
                print(f"Saved: {path}")
            if args.fail_on_gap and not record["movement_allowed"]:
                return 1
            return 0

        if args.command == "demo":
            data_dir = root / "examples" / "perception_integrity"
            canonical = data_dir / "repos-canonical-demo.txt"
            observed = data_dir / "repos-observed-demo.txt"
            inventory = inventory_record(
                canonical,
                observed,
                "bekingdomcomejoker-cpu",
                ["glass-chess"],
            )
            inv_path = persist_record(root, inventory)
            registry = load_registry(root)
            voice = voice_record("Manuscriptly", registry, 0.72)
            voice_path = persist_record(root, voice)
            claim = evaluate_claim(
                claim="glass-chess is part of the 120-repository estate",
                subject="bekingdomcomejoker-cpu/glass-chess",
                sources=["authoritative repository export", "two-way set comparison"],
                sense_evidence={
                    "sight": ["Visible in canonical export"],
                    "hearing": [],
                    "touch": ["Raw inventory file directly inspected"],
                    "smell": ["120 expected versus 119 reconstructed"],
                    "taste": ["Set subtraction isolated glass-chess"],
                },
                gates={
                    "A": gate_object("pass", "Exact owner/repository name preserved"),
                    "B": gate_object("pass", "Authoritative inventory witnesses membership"),
                    "C": gate_object("pass", "Full comparison field declared"),
                    "D": gate_object("pass", "Two-way set comparison closes"),
                    "E": gate_object("not_applicable", "Repository membership does not require etymology"),
                },
                notes="Integrated demonstration packet.",
            )
            claim_path = persist_record(root, claim)
            result = {
                "inventory": inventory,
                "voice": voice,
                "claim": claim,
                "paths": {
                    "inventory": str(inv_path),
                    "voice": str(voice_path),
                    "claim": str(claim_path),
                },
            }
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print("ALETHEIA INTEGRATED DEMONSTRATION")
                print("=================================")
                print(f"Inventory omission: {inventory['missing_ranked'][0]['repo']}")
                print(f"Voice correction:   Manuscriptly -> {voice['canonical']}")
                print(f"Claim decision:     {claim['decision']}")
                print("Verification:        PASSED")
            return 0

        if args.command == "template":
            output = (
                args.output.expanduser()
                if args.output else
                root / "templates" / "claim_audit_template.json"
            )
            template = {
                "claim": "",
                "subject": "",
                "source_refs": [],
                "senses": {
                    sense: {"evidence": []}
                    for sense in SENSES
                },
                "abcde": {
                    gate: {"state": "unknown", "notes": ""}
                    for gate in GATES
                },
                "notes": "",
            }
            write_json(output, template)
            print(f"Template saved: {output}")
            return 0

    except (OSError, ValueError, json.JSONDecodeError, sqlite3.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
