import json
from pathlib import Path

from census_engine.review import decision_payload, export_reviewed, review_status, stable_record_id


def test_stable_record_id_prefers_original_event_id():
    obj = {"original_event_id": "abc", "text": "hello"}
    assert stable_record_id(obj) == "abc"


def test_review_export(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    rec = {"original_event_id": "one", "text": "Example", "event_type_v2": "technical"}
    (data / "canon_core_357.redacted.jsonl").write_text(json.dumps(rec) + "\n", encoding="utf-8")
    for name in ["source_filename_date_witness_1392.redacted.jsonl", "date_repair_required_428.redacted.jsonl", "unconfirmed_review_26.redacted.jsonl"]:
        (data / name).write_text("", encoding="utf-8")
    state = tmp_path / "review_decisions.jsonl"
    state.write_text(json.dumps(decision_payload(rec, "canon_core", "canon")) + "\n", encoding="utf-8")
    out = tmp_path / "out.jsonl"
    count = export_reviewed(data, state, out, include="canon")
    assert count == 1
    assert "human_review_decision" in out.read_text(encoding="utf-8")
    status = review_status(data, state)
    assert status["canon"] == 1
