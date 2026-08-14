#!/usr/bin/env python3
"""Regression tests for bounded Moondream2 image ingestion."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import moondream_image as moon


class MoondreamImageTests(unittest.TestCase):
    def test_modern_command_uses_embedded_template_and_bounded_image_settings(self):
        command = moon.build_command(
            "llama-mtmd-cli",
            Path("/models/moondream2-text-model-q4_k_m-vicuna-20250414.gguf"),
            Path("/models/moondream2-mmproj-f16-20250414.gguf"),
            Path("/tmp/prepared.jpg"),
            "Describe it.",
        )
        self.assertIn("--image", command)
        self.assertIn("--mmproj", command)
        self.assertNotIn("--chat-template", command)
        self.assertNotIn("--no-jinja", command)
        self.assertNotIn("--jinja", command)
        self.assertEqual(command[command.index("--image-max-tokens") + 1], "64")
        self.assertEqual(command[command.index("-c") + 1], "1024")
        self.assertEqual(command[command.index("-b") + 1], "32")
        self.assertEqual(command[command.index("--ubatch-size") + 1], "32")
        self.assertIn("--no-mmproj-offload", command)

    def test_legacy_050824_command_keeps_vicuna_template_fallback(self):
        command = moon.build_command(
            "llama-mtmd-cli",
            Path("/models/moondream2-050824-q5k.gguf"),
            Path("/models/moondream2-mmproj-050824-f16.gguf"),
            Path("/tmp/prepared.jpg"),
            "Describe it.",
        )
        self.assertEqual(command[command.index("--chat-template") + 1], "vicuna")
        self.assertIn("--no-jinja", command)
        self.assertNotIn("--jinja", command)

    def test_defaults_select_verified_20250414_model_pair(self):
        self.assertEqual(moon.DEFAULT_MODEL.name, "moondream2-text-model-q4_k_m-vicuna-20250414.gguf")
        self.assertEqual(moon.DEFAULT_MMPROJ.name, "moondream2-mmproj-f16-20250414.gguf")

    def test_help_makes_no_html_claim(self):
        response = moon.command("help")
        self.assertIn("prepares", response.lower())
        self.assertIn("Moondream2", response)
        self.assertIn("No DeepSeek-Coder", response)

    def test_dry_run_prepares_modern_command_without_loading_a_model(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image = root / "image.jpg"
            model = root / "moondream2-text-model-q4_k_m-vicuna-20250414.gguf"
            mmproj = root / "moondream2-mmproj-f16-20250414.gguf"
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
            self.assertNotIn("--chat-template", response)


if __name__ == "__main__":
    unittest.main(verbosity=2)
