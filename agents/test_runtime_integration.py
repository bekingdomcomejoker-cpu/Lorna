#!/usr/bin/env python3
"""Regression coverage for the first Lorna runtime-integration wave."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import runtime_integration as runtime


class RuntimeIntegrationTests(unittest.TestCase):
    def test_registry_has_all_text_nodes_and_modern_vision_pair(self):
        registry = runtime.model_registry()
        self.assertEqual(set(registry["nodes"]), {"fast", "deep", "code", "agent"})
        modern = registry["vision"]["moondream_2025"]
        self.assertEqual(modern["template_mode"], "embedded")
        self.assertIn("20250414", modern["model_filename"])

    def test_auto_route_prefers_code_profile_for_code_requests(self):
        result = runtime.route_command("auto write a Python script to benchmark a model")
        self.assertIn("Auto-selected code", result)
        self.assertIn("code=tool-model", result)

    def test_pipeline_dry_run_never_launches_a_model(self):
        result = runtime.pipeline_command("--dry-run balanced explain a benchmark result")
        self.assertIn("Pipeline preview: balanced", result)
        self.assertIn("execution: sequential only", result)
        self.assertIn("1. fast: smollm-fast", result)
        self.assertIn("2. deep: deepseek-r1:1.5b", result)

    def test_pipeline_runs_stages_sequentially_and_writes_artifacts(self):
        calls = []

        def fake_chat(model, prompt):
            calls.append((model, prompt))
            return f"answer from {model}"

        with tempfile.TemporaryDirectory() as temp_dir, patch.object(runtime, "ARTIFACT_ROOT", Path(temp_dir)):
            result = runtime.run_pipeline("balanced", "Explain this task", chat=fake_chat)
            self.assertIn("Pipeline completed: balanced", result)
            self.assertEqual([model for model, _prompt in calls], ["smollm-fast", "deepseek-r1:1.5b", "smollm-fast"])
            manifests = list(Path(temp_dir).glob("*/manifest.json"))
            self.assertEqual(len(manifests), 1)
            stage_files = sorted(manifests[0].parent.glob("*.md"))
            self.assertEqual([path.name for path in stage_files], ["01_fast.md", "02_deep.md", "03_fast.md"])

    def test_system_status_has_read_only_runtime_fields(self):
        status = runtime.system_status()
        self.assertIn("memory", status)
        self.assertIn("storage", status)
        self.assertIn("binaries", status)
        self.assertIn("models", status)
        rendered = runtime.format_system_status()
        self.assertIn("Lorna runtime status:", rendered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
