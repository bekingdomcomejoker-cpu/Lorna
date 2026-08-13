"""Governed skill registry for Repo 120.

Quarantine blocks automatic execution, not operator-authorized promotion.

This module manages skill states and promotion records. It does not import or
execute skill code.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from audit_log import record_event


DEFAULT_REGISTRY = Path("runtime") / "skill_registry.json"

CALLABLE_STATES = {"ENABLED_READONLY", "ENABLED_PRIVILEGED"}
NONCALLABLE_STATES = {"QUARANTINED", "CANDIDATE", "REVIEW_REQUIRED", "BLOCKED", "DISABLED"}
VALID_STATES = CALLABLE_STATES | NONCALLABLE_STATES

READONLY_FORBIDDEN_CAPABILITIES = {"shell", "credentials", "network_mutation", "source_mutation", "delete"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SkillRecord:
    skill_id: str
    state: str = "QUARANTINED"
    adapter: Optional[str] = None
    allowed_actions: List[str] = None
    capabilities: Dict[str, bool] = None
    source_ref: Optional[str] = None
    notes: str = ""
    override: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.allowed_actions is None:
            self.allowed_actions = []
        if self.capabilities is None:
            self.capabilities = {}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_registry(path: Path = DEFAULT_REGISTRY) -> Dict[str, Any]:
    if not path.exists():
        return {"registry_version": "1.0", "skills": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_registry(registry: Dict[str, Any], path: Path = DEFAULT_REGISTRY) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    return registry


def get_skill(skill_id: str, path: Path = DEFAULT_REGISTRY) -> Optional[Dict[str, Any]]:
    return load_registry(path).get("skills", {}).get(skill_id)


def upsert_skill(record: SkillRecord, path: Path = DEFAULT_REGISTRY, actor: str = "@Operator") -> Dict[str, Any]:
    if record.state not in VALID_STATES:
        raise ValueError(f"invalid state: {record.state}")

    registry = load_registry(path)
    registry.setdefault("skills", {})[record.skill_id] = record.to_dict()
    save_registry(registry, path)

    record_event(
        actor=actor,
        event_type="skill_upsert",
        subject=record.skill_id,
        decision="recorded",
        reason="skill registry upsert",
        payload=record.to_dict(),
    )
    return record.to_dict()


def decide(skill: Optional[Dict[str, Any]], action: str) -> Dict[str, Any]:
    if not skill:
        return {"allowed": False, "reason": "SKILL_NOT_FOUND"}

    state = skill.get("state")
    if state not in CALLABLE_STATES:
        return {"allowed": False, "reason": f"SKILL_NOT_CALLABLE_STATE_{state}"}

    allowed_actions = skill.get("allowed_actions") or []
    if action not in allowed_actions:
        return {"allowed": False, "reason": "ACTION_NOT_ALLOWED"}

    capabilities = skill.get("capabilities") or {}
    if state == "ENABLED_READONLY":
        for cap in READONLY_FORBIDDEN_CAPABILITIES:
            if capabilities.get(cap):
                return {"allowed": False, "reason": f"CAPABILITY_FORBIDDEN_IN_READONLY_{cap}"}

    return {"allowed": True, "reason": "ALLOW"}


def promote(
    *,
    skill_id: str,
    target_state: str,
    approved_by: str = "@Operator",
    reason: str = "manual operator authorization",
    adapter: Optional[str] = None,
    allowed_actions: Optional[List[str]] = None,
    capabilities: Optional[Dict[str, bool]] = None,
    path: Path = DEFAULT_REGISTRY,
) -> Dict[str, Any]:
    if target_state not in VALID_STATES:
        raise ValueError(f"invalid target_state: {target_state}")

    registry = load_registry(path)
    skills = registry.setdefault("skills", {})
    item = skills.setdefault(skill_id, {"skill_id": skill_id})

    previous_state = item.get("state", "UNRECORDED")
    item["state"] = target_state
    if adapter is not None:
        item["adapter"] = adapter
    if allowed_actions is not None:
        item["allowed_actions"] = allowed_actions
    if capabilities is not None:
        item["capabilities"] = capabilities

    item["override"] = {
        "approved_by": approved_by,
        "reason": reason,
        "timestamp": utc_now(),
        "previous_state": previous_state,
        "target_state": target_state,
        "principle": "Quarantine blocks automatic execution, not operator-authorized promotion.",
    }

    save_registry(registry, path)

    record_event(
        actor=approved_by,
        event_type="skill_promotion",
        subject=skill_id,
        decision=target_state,
        reason=reason,
        payload=item,
    )

    return item
