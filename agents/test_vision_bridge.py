#!/usr/bin/env python3
"""Regression tests for the Lorna2 SmolVLM-to-Moondream2 bridge."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import vision_bridge as bridge


class VisionBridgeTests(unittest.TestCase):
    def test_moondream_stage_is_text_only_and_bounded(self):
        command = bridge.build_moondream_text_command(
            "llama-cli",
            Path("/models/moondream2.gguf"),
            "layout: a card",
            "What is the purpose?",
        )
        self.assertEqual(command[:3], ["llama-cli", "-m", "/models/moondream2.gguf"])
        self.assertNotIn("--image", command)
        self.assertNotIn("--mmproj", command)
        self.assertEqual(command[command.index("-n") + 1], "96")
        self.assertIn("layout: a card", command[command.index("-p") + 1])

    def test_help_describes_sequential_no_html_bridge(self):
        response = bridge.command("help")
        self.assertIn("SmolVLM first", response)
        self.assertIn("Moondream2", response)
        self.assertIn("No HTML", response)

    def test_dry_run_validates_files_and_builds_only_first_stage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image = root / "image.png"
            vision_model = root / "smolvlm.gguf"
            mmproj = root / "mmproj.gguf"
            moondream_model = root / "moondream2.gguf"
            for path in (image, vision_model, mmproj, moondream_model):
                path.write_text("fixture", encoding="utf-8")
            args = bridge.make_parser().parse_args(
                [
                    str(image),
                    "--vision-model", str(vision_model),
                    "--mmproj", str(mmproj),
                    "--moondream-model", str(moondream_model),
                    "--work-dir", str(root / "work"),
                    "--dry-run",
                ]
            )
            with patch.object(bridge, "_which", side_effect=lambda name: f"/bin/{name}"), patch.object(
                bridge, "_is_ollama_running", return_value=False
            ):
                response = bridge.run_bridge(args)
            self.assertIn("Dry run", response)
            self.assertIn("llama-mtmd-cli", response)
            self.assertIn("Moondream2", response)


if __name__ == "__main__":
    unittest.main(verbosity=2)
