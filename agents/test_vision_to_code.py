#!/usr/bin/env python3
"""Regression tests for Lorna2's sequential SmolVLM-to-DeepSeek-Coder pipeline."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import vision_to_code as pipeline


class VisionToCodeTests(unittest.TestCase):
    def test_vision_command_uses_mtmd_safe_template_and_memory_limits(self):
        command = pipeline.build_vision_command(
            "llama-mtmd-cli",
            Path("/models/smolvlm.gguf"),
            Path("/models/mmproj.gguf"),
            Path("/images/source.png"),
        )
        self.assertIn("--no-jinja", command)
        self.assertIn("-sys", command)
        self.assertIn("--grammar-file", command)
        self.assertEqual(command[command.index("--grammar-file") + 1], str(pipeline.VISUAL_SPEC_GRAMMAR))
        self.assertTrue(pipeline.VISUAL_SPEC_GRAMMAR.is_file())
        grammar = pipeline.VISUAL_SPEC_GRAMMAR.read_text(encoding="utf-8")
        self.assertNotIn("\\\\-", grammar)
        self.assertIn("--chat-template", command)
        self.assertEqual(command[command.index("--chat-template") + 1], "smolvlm")
        self.assertIn("--image-max-tokens", command)
        self.assertEqual(command[command.index("--image-max-tokens") + 1], "128")
        self.assertNotIn("--no-mmproj-offload", command)
        self.assertNotIn("--mmproj-offload", command)
        self.assertIn("--cache-type-k", command)
        forced_off = pipeline.build_vision_command(
            "llama-mtmd-cli", Path("/models/smolvlm.gguf"), Path("/models/mmproj.gguf"), Path("/images/source.png"), projector_offload="off"
        )
        self.assertIn("--no-mmproj-offload", forced_off)
        forced_on = pipeline.build_vision_command(
            "llama-mtmd-cli", Path("/models/smolvlm.gguf"), Path("/models/mmproj.gguf"), Path("/images/source.png"), projector_offload="on"
        )
        self.assertIn("--mmproj-offload", forced_on)

    def test_adaptive_image_preparation_resizes_large_input(self):
        if pipeline.Image is None:
            self.skipTest("Pillow is unavailable")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.png"
            pipeline.Image.new("RGB", (2000, 1000), color=(20, 40, 60)).save(source)
            prepared = pipeline._prepare_image(source, root / "work", 1280, 80, True)
            self.assertEqual(prepared.path.suffix.lower(), ".jpg")
            with pipeline.Image.open(prepared.path) as image:
                self.assertEqual(image.size, (1280, 640))
            self.assertIn("resized", prepared.summary)

    def test_visual_spec_extraction_ignores_runtime_logs(self):
        raw = (
            "0.01.000 I mtmd: loading\n"
            "BEGIN_VISUAL_SPEC\n"
            "layout: white page\nelements: button\nstyle: simple\ntext: unreadable\n"
            "END_VISUAL_SPEC\n"
            "0.10.000 I perf done\n"
        )
        self.assertEqual(
            pipeline._strip_stage_logs(raw),
            "layout: white page\nelements: button\nstyle: simple\ntext: unreadable",
        )

    def test_unstructured_vision_text_is_rejected(self):
        self.assertEqual(
            pipeline._strip_stage_logs("0.10.000 I loading\nScreen displaying a code reconstruction page.\n"),
            "",
        )

    def test_main_fragment_is_wrapped_in_a_standalone_page(self):
        raw = """<|im_start|>html
<main><section><h1>Compact</h1><button>Continue</button></section></main>
<|im_end|>"""
        result = pipeline._extract_generated_source(raw, Path("/tmp/rebuilt.html"))
        self.assertIn("<!doctype html>", result.lower())
        self.assertIn("<main><section><h1>Compact</h1><button>Continue</button></section></main>", result)
        self.assertIn("</html>", result)

    def test_complete_html_is_recovered_after_template_and_fences(self):
        raw = """SOLUTION:
<|im_start|>assistant
<|im_end|>
```html
<html><body><main>Recovered</main></body></html>
```
```
```
"""
        result = pipeline._extract_generated_source(raw, Path("/tmp/rebuilt.html"))
        self.assertEqual(result, "<html><body><main>Recovered</main></body></html>\n")

    def test_deepseek_template_output_becomes_self_contained_html(self):
        raw = """SOLUTION:
<|im_start|>html
<div class=\"card\">Hello</div>
<|im_end|>
<|im_start|>css
.card { color: blue; }
<|im_end|>
The HTML and CSS code provided above is an example.
"""
        result = pipeline._extract_generated_source(raw, Path("/tmp/rebuilt.html"))
        self.assertIn("<!doctype html>", result.lower())
        self.assertIn(".card { color: blue; }", result)
        self.assertIn('<div class="card">Hello</div>', result)
        self.assertNotIn("The HTML and CSS code", result)

    def test_help_command_describes_sequential_memory_safe_behavior(self):
        response = pipeline.command("help")
        self.assertIn("SmolVLM first", response)
        self.assertIn("DeepSeek-Coder", response)

    def test_missing_files_stop_before_a_model_is_launched(self):
        args = pipeline.make_parser().parse_args(["/missing/screenshot.png"])
        with patch.object(pipeline, "_which", side_effect=lambda name: f"/bin/{name}"):
            response = pipeline.run_pipeline(args)
        self.assertIn("missing required file", response)

    def test_cancelled_stage_returns_a_clean_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "cancelled.log"
            with patch("subprocess.run", side_effect=KeyboardInterrupt):
                status, stdout, combined = pipeline._run_stage(
                    ["fake-model"], 1, log_path, "Fake stage"
                )
            self.assertEqual(status, 130)
            self.assertEqual(stdout, "")
            self.assertIn("cancelled", combined)
            self.assertIn("cancelled", log_path.read_text(encoding="utf-8"))

    def test_coder_command_uses_bounded_raw_prompting(self):
        with patch.object(pipeline, "_help_contains", side_effect=lambda _binary, option: option in {"--no-conversation", "--no-jinja"}):
            command = pipeline.build_coder_command("llama-cli", Path("/models/coder.gguf"), Path("/tmp/prompt.txt"), Path("/tmp/output.html"))
        self.assertEqual(command[command.index("-n") + 1], "224")
        self.assertIn("--no-conversation", command)
        self.assertIn("--no-jinja", command)
        self.assertNotIn("--single-turn", command)

    def test_dry_run_builds_both_stages_without_launching(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image = root / "image.png"
            vision_model = root / "vision.gguf"
            mmproj = root / "mmproj.gguf"
            coder_model = root / "coder.gguf"
            for path in (image, vision_model, mmproj, coder_model):
                path.write_text("fixture", encoding="utf-8")
            args = pipeline.make_parser().parse_args(
                [
                    str(image),
                    "--vision-model", str(vision_model),
                    "--mmproj", str(mmproj),
                    "--coder-model", str(coder_model),
                    "--work-dir", str(root / "work"),
                    "--dry-run",
                ]
            )
            with patch.object(pipeline, "_which", side_effect=lambda name: f"/bin/{name}"), patch.object(
                pipeline, "_is_ollama_running", return_value=False
            ), patch.object(pipeline, "_help_contains", return_value=False):
                response = pipeline.run_pipeline(args)
            self.assertIn("Dry run", response)
            self.assertIn("llama-mtmd-cli", response)
            self.assertIn("llama-cli", response)
            self.assertIn("--no-jinja", response)


if __name__ == "__main__":
    unittest.main(verbosity=2)
