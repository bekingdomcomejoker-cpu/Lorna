#!/usr/bin/env python3
"""Prepared-image Moondream2 ingestion for memory-constrained Termux.

The image is resized and recompressed before Moondream2's own projector sees it.
SmolVLM is not loaded here: visual projectors are model-specific, so its encoded
features cannot be passed to Moondream2.  The shared, useful bridge is the
prepared-image asset and the bounded direct multimodal invocation.
"""

from __future__ import annotations

import argparse
import re
import shlex
from pathlib import Path
from time import monotonic

try:
    from .vision_to_code import (
        DEFAULT_WORK_DIR,
        HOME,
        _format_seconds,
        _is_ollama_running,
        _prepare_image,
        _run_stage,
        _validate_paths,
        _which,
    )
except ImportError:
    from vision_to_code import (
        DEFAULT_WORK_DIR,
        HOME,
        _format_seconds,
        _is_ollama_running,
        _prepare_image,
        _run_stage,
        _validate_paths,
        _which,
    )

DEFAULT_MODEL = HOME / "models" / "moondream2-050824-q5k.gguf"
DEFAULT_MMPROJ = HOME / "models" / "moondream2-mmproj-050824-f16.gguf"
DEFAULT_WORK_DIR = DEFAULT_WORK_DIR / "moondream2_image"


def build_command(
    mtmd_cli: str,
    model: Path,
    mmproj: Path,
    image: Path,
    question: str,
    context: int = 1024,
    batch: int = 32,
    ubatch: int = 32,
    image_max_tokens: int = 64,
) -> list[str]:
    """Build the direct, bounded Moondream2 image command."""
    return [
        mtmd_cli,
        "-m",
        str(model),
        "--mmproj",
        str(mmproj),
        "--image",
        str(image),
        "-p",
        question,
        "--no-jinja",
        "--chat-template",
        "vicuna",
        "-n",
        "64",
        "-c",
        str(context),
        "-t",
        "4",
        "-b",
        str(batch),
        "--ubatch-size",
        str(ubatch),
        "--cache-type-k",
        "q4_0",
        "--cache-type-v",
        "q4_0",
        "--no-mmproj-offload",
        "--image-max-tokens",
        str(image_max_tokens),
        "--temp",
        "0.1",
        "--perf",
    ]


def _clean_response(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^\d+\.\d+\.\d+\s+[IWE]\s", stripped):
            continue
        if stripped.startswith(("build", "model", "ftype", "modalities", "available commands:", "Loaded media")):
            continue
        if stripped.startswith(("/exit", "/regen", "/clear", "/read", "/glob", ">")):
            continue
        if "chat template example" in stripped:
            continue
        lines.append(stripped)
    return "\n".join(lines).strip()


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare an image and run direct bounded Moondream2 ingestion.")
    parser.add_argument("image", help="Local image or screenshot to inspect")
    parser.add_argument("--question", default="Describe the image in one short sentence.")
    parser.add_argument("--model", default=str(DEFAULT_MODEL))
    parser.add_argument("--mmproj", default=str(DEFAULT_MMPROJ))
    parser.add_argument("--work-dir", default=str(DEFAULT_WORK_DIR))
    parser.add_argument("--context", type=int, default=1024)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--ubatch", type=int, default=32)
    parser.add_argument("--image-max-tokens", type=int, default=64)
    parser.add_argument("--max-image-edge", type=int, default=512)
    parser.add_argument("--jpeg-quality", type=int, default=70)
    parser.add_argument("--no-preprocess", action="store_true")
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--allow-ollama", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def run(args: argparse.Namespace) -> str:
    image = Path(args.image).expanduser().resolve()
    model = Path(args.model).expanduser().resolve()
    mmproj = Path(args.mmproj).expanduser().resolve()
    work_dir = Path(args.work_dir).expanduser().resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    result_path = work_dir / "moondream2_response.md"
    log_path = work_dir / "moondream2_image.log"

    mtmd_cli = _which("llama-mtmd-cli")
    if not mtmd_cli:
        return "Moondream2 image ingestion unavailable: llama-mtmd-cli is not installed."
    missing = _validate_paths([image, model, mmproj])
    if missing:
        return "Moondream2 image ingestion stopped; missing required file(s):\n  " + "\n  ".join(missing)
    if _is_ollama_running() and not args.allow_ollama:
        return "Moondream2 image ingestion stopped because `ollama serve` is running. Stop it first to free memory."

    prepared = _prepare_image(image, work_dir, args.max_image_edge, args.jpeg_quality, not args.no_preprocess)
    command = build_command(
        mtmd_cli,
        model,
        mmproj,
        prepared.path,
        args.question,
        args.context,
        args.batch,
        args.ubatch,
        args.image_max_tokens,
    )
    if args.dry_run:
        return (
            "Dry run: image preparation plus bounded direct Moondream2 ingestion.\n\n"
            f"Prepared image: {prepared.path} ({prepared.summary})\n\n"
            f"Command:\n{shlex.join(command)}"
        )

    print(f"Prepared image: {prepared.summary}", flush=True)
    print(
        "Starting direct Moondream2 image ingestion with a 240-second limit. "
        "This short-question profile uses ctx=1024 and batch/ubatch=32.",
        flush=True,
    )
    started = monotonic()
    status, stdout, output = _run_stage(command, args.timeout, log_path, "Moondream2 image stage", live_output=True)
    elapsed = monotonic() - started
    if status != 0:
        return f"Moondream2 image stage ended with exit code {status} after {_format_seconds(elapsed)}. Log: {log_path}"

    response = _clean_response(stdout or output)
    if not response:
        return f"Moondream2 finished without recoverable response text after {_format_seconds(elapsed)}. Log: {log_path}"
    result_path.write_text(response + "\n", encoding="utf-8")
    return (
        "Moondream2 direct image ingestion completed.\n"
        f"Prepared image: {prepared.path}\n"
        f"Response: {result_path}\n"
        f"Timing: {_format_seconds(elapsed)}\n"
        f"Log: {log_path}"
    )


def command(argument: str) -> str:
    try:
        values = shlex.split(argument)
    except ValueError as exc:
        return f"Invalid /moondream-image arguments: {exc}"
    if not values or values[0] in {"help", "--help", "-h"}:
        return (
            "Usage: /moondream-image <image> [question]\n"
            "Prepares a smaller JPEG and sends it directly to Moondream2 with its paired projector. "
            "No DeepSeek-Coder or HTML stage is used."
        )
    parser = make_parser()
    argv = [values[0]]
    if len(values) > 1:
        argv.extend(["--question", values[1]])
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return "Usage: /moondream-image <image> [question]"
    return run(args)


if __name__ == "__main__":
    print(run(make_parser().parse_args()))
