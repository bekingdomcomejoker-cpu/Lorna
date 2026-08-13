import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "omega_router"))

from skill_registry import SkillRecord, decide, promote, upsert_skill


def test_quarantined_skill_not_callable(tmp_path):
    registry = tmp_path / "skills.json"
    upsert_skill(SkillRecord(skill_id="x", state="QUARANTINED"), path=registry)

    skill = {
        "skill_id": "x",
        "state": "QUARANTINED",
        "allowed_actions": ["run"],
        "capabilities": {},
    }

    decision = decide(skill, "run")
    assert decision["allowed"] is False
    assert decision["reason"] == "SKILL_NOT_CALLABLE_STATE_QUARANTINED"


def test_operator_promotion_records_override(tmp_path):
    registry = tmp_path / "skills.json"

    item = promote(
        skill_id="music-prompter",
        target_state="ENABLED_READONLY",
        approved_by="@Operator",
        reason="manual owner override",
        adapter="omega.adapters.music_prompter_adapter",
        allowed_actions=["prompt"],
        capabilities={"shell": False, "credentials": False, "network_mutation": False, "source_mutation": False},
        path=registry,
    )

    assert item["state"] == "ENABLED_READONLY"
    assert item["override"]["approved_by"] == "@Operator"
    assert "Quarantine blocks automatic execution" in item["override"]["principle"]


def test_readonly_blocks_forbidden_capabilities():
    skill = {
        "skill_id": "bad",
        "state": "ENABLED_READONLY",
        "allowed_actions": ["run"],
        "capabilities": {"shell": True},
    }
    decision = decide(skill, "run")
    assert decision["allowed"] is False
    assert decision["reason"] == "CAPABILITY_FORBIDDEN_IN_READONLY_shell"


def test_enabled_privileged_allows_declared_action():
    skill = {
        "skill_id": "privileged",
        "state": "ENABLED_PRIVILEGED",
        "allowed_actions": ["promote"],
        "capabilities": {"write_files": True},
    }
    decision = decide(skill, "promote")
    assert decision["allowed"] is True
