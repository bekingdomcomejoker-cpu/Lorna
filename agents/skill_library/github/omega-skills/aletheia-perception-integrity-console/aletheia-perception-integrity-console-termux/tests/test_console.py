#!/usr/bin/env python3
from __future__ import annotations
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

base = Path(sys.argv[1])
tool = base / "tools" / "aletheia-console"

def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(tool), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

status = run("status", "--root", str(base))
assert status.returncode == 0, status.stdout

demo = run("demo", "--root", str(base), "--json")
assert demo.returncode == 0, demo.stdout
payload = json.loads(demo.stdout)
assert payload["inventory"]["missing_ranked"][0]["repo"] == "bekingdomcomejoker-cpu/glass-chess"
assert payload["voice"]["canonical"] == "Node 4 / Manus"
assert payload["claim"]["decision"] == "ALLOW"

voice = run("voice", "nonsense phrase with no registry match", "--root", str(base), "--json")
assert voice.returncode == 1, voice.stdout
voice_payload = json.loads(voice.stdout)
assert voice_payload["decision"] == "HOLD_FOR_OPERATOR_CORRECTION"
assert voice_payload["create_new_entity"] is False

db = base / "state" / "cat_eof.db"
assert db.exists()
with sqlite3.connect(db) as connection:
    count = connection.execute("SELECT COUNT(*) FROM perception_records").fetchone()[0]
    assert count >= 4

print("PERCEPTION INTEGRITY CONSOLE VERIFICATION PASSED")
print("Glass-Chess omission detected")
print("Manuscriptly -> Node 4 / Manus")
print("Unknown speech preserved without creating a new entity")
