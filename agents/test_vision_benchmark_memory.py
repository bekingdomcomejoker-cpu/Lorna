#!/usr/bin/env python3
"""Regression tests for durable Lorna2 vision benchmark memory."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vision_benchmark_memory import (
    format_profile,
    format_results,
    ingest,
    load_memory,
    parse_summary,
)


class VisionBenchmarkMemoryTests(unittest.TestCase):
    def write_summary(self, root: Path, *, dry_run: bool = False) -> Path:
        moon_log = root / "moondream2-1.log"
        smol_log = root / "smolvlm-1.log"
        slow_moon_log = root / "moondream2-2.log"
        moon_log.write_text(
            "0.53.947 I mtmd batch encoding done in 37446 ms\n\n"
            "The image features a blue square, a green circle, and a red triangle.\n"
            "[ Prompt: 1.0 t/s | Generation: 2.0 t/s ]\n",
            encoding="utf-8",
        )
        smol_log.write_text(
            "0.14.056 I mtmd batch encoding done in 11339 ms\n\n"
            "A geometric-shape fixture on a white background.\n",
            encoding="utf-8",
        )
        slow_moon_log.write_text(
            "0.59.276 I mtmd batch encoding done in 43936 ms\n\n"
            "The fixture contains colored shapes.\n",
            encoding="utf-8",
        )
        mode = "dry-run" if dry_run else "benchmark"
        summary = root / "summary.txt"
        summary.write_text(
            "Lorna sequential vision benchmark\n"
            "timeout=180s per model\n"
            "mode=one-variable-at-a-time\n"
            f"mode={mode}\n"
            f"Moondream2 | baseline | t=4 tb=4 n=24 image=64 | exit=0 | elapsed=45s | log={moon_log}\n"
            f"SmolVLM | baseline | t=4 tb=4 n=32 image=auto | exit=0 | elapsed=16s | log={smol_log}\n"
            f"Moondream2 | threads=2 | t=2 tb=2 n=24 image=64 | exit=0 | elapsed=62s | log={slow_moon_log}\n",
            encoding="utf-8",
        )
        return summary

    def test_parse_summary_extracts_paired_configs_and_responses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            summary = self.write_summary(Path(directory))
            records = parse_summary(summary)

        self.assertEqual(3, len(records))
        self.assertEqual("moondream_2025", records[0]["model_pair"])
        self.assertEqual({"threads": 4, "batch_threads": 4, "output_tokens": 24, "image_tokens": "64"}, records[0]["config"])
        self.assertTrue(records[0]["encoding_done"])
        self.assertIn("blue square", records[0]["response_text"])
        self.assertTrue(records[1]["completed_successfully"])

    def test_ingestion_is_idempotent_and_selects_fastest_encoded_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary = self.write_summary(root)
            memory_path = root / "benchmark_memory.json"
            added, parsed = ingest(summary, memory_path)
            added_again, parsed_again = ingest(summary, memory_path)
            memory = load_memory(memory_path)

        self.assertEqual((3, 3), (added, parsed))
        self.assertEqual((0, 3), (added_again, parsed_again))
        self.assertEqual(3, len(memory["vision_runs"]))
        self.assertEqual(45.0, memory["vision_recommendations"]["moondream_2025"]["elapsed_s"])
        self.assertEqual(16.0, memory["vision_recommendations"]["smolvlm"]["elapsed_s"])

    def test_dry_run_records_do_not_create_recommendations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary = self.write_summary(root, dry_run=True)
            memory_path = root / "benchmark_memory.json"
            ingest(summary, memory_path)
            memory = load_memory(memory_path)

        self.assertEqual({}, memory["vision_recommendations"])
        self.assertTrue(all(run["dry_run"] for run in memory["vision_runs"]))
        self.assertTrue(all(not run["completed_successfully"] for run in memory["vision_runs"]))

    def test_result_and_profile_formatters_do_not_launch_models(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary = self.write_summary(root)
            memory_path = root / "benchmark_memory.json"
            ingest(summary, memory_path)
            result_output = format_results("smolvlm 1", memory_path)
            profile_output = format_profile("moondream_2025", memory_path)

        self.assertIn("smolvlm [baseline]", result_output)
        self.assertIn("moondream_2025: t=4 tb=4 n=24 image=64", profile_output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
