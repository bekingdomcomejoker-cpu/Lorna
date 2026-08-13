import json
import os
import tempfile
import unittest
from pathlib import Path

class FederationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["CAT_EOF_HOME"] = self.tmp.name
        import federation.core as c
        self.c = c
        base = Path(self.tmp.name)
        c.BASE = base
        c.APP = base/"apps"/"omega-sovereign-federation"
        c.STATE = base/"state"
        c.OUTPUT = base/"output"/"federation"
        c.REGISTRY = base/"registry"
        c.AGENT_PENDING = base/"agent_queue"/"pending"
        c.AGENT_COMPLETE = base/"agent_queue"/"complete"
        c.DB = c.STATE/"cat_eof.db"
        c.JSONL = c.STATE/"perception_integrity.jsonl"
        c.FED_BUS = c.STATE/"federation_bus.jsonl"
        c.CAT_BUS = base/"cat_bus.jsonl"
        c.COMM_BUS = base/"comm_bus.jsonl"
        c.VOICE_REGISTRY = c.REGISTRY/"voice_registry.json"
        c.ensure_dirs()

    def tearDown(self):
        self.tmp.cleanup()

    def test_hard_gate_missing_blocks_verified(self):
        result = self.c.hard_gate(
            {k:"STRONG" for k in ["hearing","sight","touch","smell","taste"]},
            {"A":"CONFIRMED","B":"CONFIRMED","C":"CONFIRMED","D":"MISSING","E":"CONFIRMED"},
        )
        self.assertEqual(result["verdict"], "HOLD")

    def test_inventory_detects_glass_chess(self):
        canonical = Path(self.tmp.name)/"canonical.txt"
        observed = Path(self.tmp.name)/"observed.txt"
        canonical.write_text("owner/omega\nowner/glass-chess\n")
        observed.write_text("owner/omega\n")
        result = self.c.audit_inventory(str(canonical), str(observed), "owner/glass-chess")
        self.assertIn("owner/glass-chess", result["missing"])
        self.assertFalse(result["canary_present"])

    def test_voice_unknown_preserved(self):
        result = self.c.voice_resolve("Entirely New Phrase")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNone(result["canonical"])

    def test_voice_known_corrected(self):
        self.c.VOICE_REGISTRY.write_text(json.dumps({
            "manuscriptly":{"canonical":"Node 4 / Manus"}
        }))
        result = self.c.voice_resolve("Manuscriptly")
        self.assertEqual(result["canonical"], "Node 4 / Manus")

    def test_agent_packet(self):
        result = self.c.create_agent_packet("Research the archive", {"source":"test"})
        self.assertTrue(Path(result["path"]).exists())
        self.assertEqual(result["packet"]["status"], "PENDING")

    def test_ledger_hash(self):
        r = self.c.save_record({"record_type":"test","status":"ok"})
        self.assertEqual(len(r["sha256"]), 64)
        self.assertEqual(len(self.c.ledger(10)), 1)

    def test_marker(self):
        route, prompt = self.c.parse_marker("@code inspect this", "auto")
        self.assertEqual(route, "code")
        self.assertEqual(prompt, "inspect this")

    def test_text_count_is_explicit(self):
        p = Path(self.tmp.name)/"t.txt"
        p.write_text("one two three")
        result = self.c.count_text(str(p), 3, "whitespace")
        self.assertTrue(result["passed"])
        self.assertIn("does not establish", result["boundary"])

if __name__ == "__main__":
    unittest.main()
