#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SERVER = HERE / "backend" / "server.py"

with tempfile.TemporaryDirectory() as temp:
    os.environ["CAT_EOF_HOME"] = temp
    spec = importlib.util.spec_from_file_location("bridge", SERVER)
    bridge = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(bridge)

    bridge.BASE = Path(temp)
    bridge.STATE = bridge.BASE / "state"
    bridge.JSONL = bridge.STATE / "perception_integrity.jsonl"
    bridge.DB = bridge.STATE / "cat_eof.db"

    record = bridge.save_record(
        {
            "record_type": "smoke_test",
            "case_id": "case-smoke",
            "raw": {"who": "Dominique"},
            "computed": {"decision": "UNKNOWN"},
        }
    )

    assert record["record_id"].startswith("record-")
    assert bridge.JSONL.exists()
    rows = bridge.ledger(10)
    assert len(rows) == 1
    assert rows[0]["record_type"] == "smoke_test"

print("CLAUDE BRIDGE SMOKE TEST PASSED")
print("JSONL and SQLite persistence verified")
