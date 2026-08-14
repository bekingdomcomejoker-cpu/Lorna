#!/usr/bin/env python3
"""Regression tests for bounded Moondream2 image ingestion."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import moondream_image as moon


class MoondreamImageTests(unittest.TestCase):
    def test_command_uses_alpaca_template_and_bounded_image_settings(self):
        command = moon.build_command(
            "llama-mtmd-cli",
            Path("/models/moondream.gguf"),
            Path("/models/mmproj.gguf"),
            Path("/tmp/prepared.jpg"),
            "Describe it.",
        )
        self.assertIn("--image", command)
        self.assertIn("--mmproj", command)
        self.assertEqual(command[command.index("--chat-template") + 1], "alpaca")
        self.assertIn("--jinja", command)
        self.assertNotIn("--no-jinja", command)
        self.assertEqual(command[command.index("--image-max-tokens") + 1], "64")
        self.assertEqual(command[command.index("-c") + 1], "2048")
        self.assertIn("--no-mmproj-offload", command)

    def test_help_makes_no_html_claim(self):
        response = moon.command("help")
        self.assertIn("prepares", response.lower())
        self.assertIn("Moondream2", response)
        self.assertIn("No DeepSeek-Coder", response)

    def test_dry_run_prepares_command_without_loading_a_model(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image = root / "image.jpg"
            model = root / "moondream.gguf"
            mmproj = root / "mmproj.gguf"
            for path in (image, model, mmproj):
                path.write_text("fixture", encoding="utf-8")
            args = moon.make_parser().parse_args(
                [str(image), "--model", str(model), "--mmproj", str(mmproj), "--work-dir", str(root / "work"), "--dry-run"]
            )
            with patch.object(moon, "_which", return_value="/bin/llama-mtmd-cli"), patch.object(
                moon, "_is_ollama_running", return_value=False
            ):
                response = moon.run(args)
            self.assertIn("Dry run", response)
            self.assertIn("--chat-template alpaca", response)


if __name__ == "__main__":
    unittest.main(verbosity=2)
