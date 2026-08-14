#!/usr/bin/env python3
"""Sequential SmolVLM-to-Moondream2 bridge for memory-constrained Termux.

SmolVLM performs the image pass first and exits.  Moondream2 then receives the
saved visual specification as text for a compact second-stage interpretation.
The models never coexist in memory and this command deliberately generates no
HTML or source code.
"""

from __future__ import annotations

import argparse
import shlex
from pathlib import Path
from time import monotonic

try:
    from .vision_to_code import (
        DEFAULT_MMPROJ,
        DEFAULT_VISION_MODEL,
        DEFAULT_WORK_DIR,
        HOME,
        _format_seconds,
        _is_ollama_running,
        _prepare_image,
        _run_stage,
        _strip_stage_logs,
        _validate_paths,
        _which,
        build_vision_command,
    )
except ImportError:
    from vision_to_code import (
        DEFAULT_MMPROJ,
        DEFAULT_VISION_MODEL,
        DEFAULT_WORK_DIR,
        HOME,
        _format_seconds,
        _is_ollama_running,
        _prepare_image,
        _run_stage,
        _strip_stage_logs,
        _validate_paths,
        _which,
        build_vision_command,
    )

DEFAULT_MOONDREAM_MODEL = HOME / "models" / "moondream2-050824-q5k.gguf"
DEFAULT_BRIDGE_DIR = DEFAULT_WORK_DIR / "smolvlm_to_moondream2"


def build_moondream_text_command(
    llama_cli: str,
    model: Path,
    visual_spec: str,
    question: str,
) -> list[str]:
    """Build the small text-only Moondream2 interpretation stage."""
    prompt = (
        "A first visual model produced this image report:\n"
        f"{visual_spec}\n\n"
        f"Task: {question}\n"
        "Give a concise interpretation using only the report."
    )
    return [
        llama_cli,
        "-m",
        str(model),
        "-p",
        prompt,
        "-n",
        "96",
        "-c",
        "512",
        "-t",
        "4",
        "-b",
        "16",
        "--temp",
        "0.1",
        "--no-perf",
    ]


def _paths(work_dir: Path) -> dict[str, Path]:
    work_dir.mkdir(parents=True, exist_ok=True)
    return {
        "work_dir": work_dir,
        "vision_log": work_dir / "smolvlm_bridge.log",
        "visual_spec": work_dir / "smolvlm_visual_spec.md",
        "moondream_log": work_dir / "moondream2_bridge.log",
        "result": work_dir / "moondream2_interpretation.md",
    }


def run_bridge(args: argparse.Namespace) -> str:
    image = Path(args.image).expanduser().resolve()
    vision_model = Path(args.vision_model).expanduser().resolve()
    mmproj = Path(args.mmproj).expanduser().resolve()
    moondream_model = Path(args.moondream_model).expanduser().resolve()
    work_dir = Path(args.work_dir).expanduser().resolve()
    paths = _paths(work_dir)

    mtmd_cli = _which("llama-mtmd-cli")
    llama_cli = _which("llama-cli")
    if not mtmd_cli or not llama_cli:
        return "Vision bridge unavailable: both llama-mtmd-cli and llama-cli must be installed."

    missing = _validate_paths([image, vision_model, mmproj, moondream_model])
    if missing:
        return "Vision bridge stopped; missing required file(s):\n  " + "\n  ".join(missing)
    if _is_ollama_running() and not args.allow_ollama:
        return (
            "Vision bridge stopped before loading models because `ollama serve` is running. "
            "Stop Ollama first to free memory, then rerun."
        )

    preparation_started = monotonic()
    prepared = _prepare_image(
        image,
        paths["work_dir"],
        args.max_image_edge,
        args.jpeg_quality,
        not args.no_preprocess,
    )
    preparation_seconds = monotonic() - preparation_started
    vision_command = build_vision_command(
        mtmd_cli,
        vision_model,
        mmproj,
        prepared.path,
        context=args.context,
        batch=args.batch,
        ubatch=args.ubatch,
        image_max_tokens=args.image_max_tokens,
        projector_offload=args.projector_offload,
    )

    if args.dry_run:
        return (
            "Dry run: SmolVLM would analyze the image, exit, then Moondream2 would "
            "interpret the saved report.\n\n"
            f"SmolVLM command:\n{shlex.join(vision_command)}\n\n"
            f"Work directory: {paths['work_dir']}"
        )

    print(f"Image preparation: {prepared.summary} ({_format_seconds(preparation_seconds)})", flush=True)
    print("Starting SmolVLM bridge stage. Wait while image batches advance.", flush=True)
    vision_started = monotonic()
    vision_status, _vision_stdout, vision_output = _run_stage(
        vision_command,
        args.vision_timeout,
        paths["vision_log"],
        "SmolVLM bridge stage",
        live_output=True,
    )
    vision_seconds = monotonic() - vision_started
    if vision_status != 0:
        return f"SmolVLM bridge stage failed with exit code {vision_status}. Log: {paths['vision_log']}"

    visual_spec = _strip_stage_logs(vision_output)
    if not visual_spec:
        return (
            "SmolVLM completed without a strict visual specification. Moondream2 was not started. "
            f"Inspect: {paths['vision_log']}"
        )
    paths["visual_spec"].write_text(visual_spec + "\n", encoding="utf-8")

    moondream_command = build_moondream_text_command(
        llama_cli,
        moondream_model,
        visual_spec,
        args.question,
    )
    print(f"SmolVLM completed in {_format_seconds(vision_seconds)}. Starting text-only Moondream2 bridge stage.", flush=True)
    moon_started = monotonic()
    moon_status, moon_stdout, moon_output = _run_stage(
        moondream_command,
        args.moondream_timeout,
        paths["moondream_log"],
        "Moondream2 bridge stage",
        live_output=True,
    )
    moon_seconds = monotonic() - moon_started
    if moon_status != 0:
        return (
            f"Moondream2 bridge stage failed with exit code {moon_status}. "
            f"Visual spec remains at: {paths['visual_spec']}\n"
            f"Log: {paths['moondream_log']}"
        )

    interpretation = (moon_stdout or moon_output).strip()
    if not interpretation:
        return (
            "Moondream2 completed without an interpretation. "
            f"Visual spec remains at: {paths['visual_spec']}\n"
            f"Log: {paths['moondream_log']}"
        )
    paths["result"].write_text(interpretation + "\n", encoding="utf-8")
    return (
        "SmolVLM-to-Moondream2 bridge completed sequentially.\n"
        f"Visual specification: {paths['visual_spec']}\n"
        f"Moondream2 interpretation: {paths['result']}\n"
        f"Timing: preparation={_format_seconds(preparation_seconds)}, "
        f"SmolVLM={_format_seconds(vision_seconds)}, Moondream2={_format_seconds(moon_seconds)}\n"
        f"Logs: {paths['vision_log']} and {paths['moondream_log']}"
    )


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run SmolVLM first, then a text-only Moondream2 interpretation.")
    parser.add_argument("image", help="Local image or screenshot to analyze")
    parser.add_argument("--question", default="Summarize the important visual structure and likely user purpose.")
    parser.add_argument("--vision-model", default=str(DEFAULT_VISION_MODEL))
    parser.add_argument("--mmproj", default=str(DEFAULT_MMPROJ))
    parser.add_argument("--moondream-model", default=str(DEFAULT_MOONDREAM_MODEL))
    parser.add_argument("--work-dir", default=str(DEFAULT_BRIDGE_DIR))
    parser.add_argument("--context", type=int, default=2048)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--ubatch", type=int, default=8)
    parser.add_argument("--image-max-tokens", type=int, default=128)
    parser.add_argument("--max-image-edge", type=int, default=1280)
    parser.add_argument("--jpeg-quality", type=int, default=80)
    parser.add_argument("--no-preprocess", action="store_true")
    parser.add_argument("--projector-offload", choices=("auto", "on", "off"), default="auto")
    parser.add_argument("--vision-timeout", type=int, default=240)
    parser.add_argument("--moondream-timeout", type=int, default=120)
    parser.add_argument("--allow-ollama", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def command(argument: str) -> str:
    try:
        values = shlex.split(argument)
    except ValueError as exc:
        return f"Invalid /vision-bridge arguments: {exc}"
    if not values or values[0] in {"help", "--help", "-h"}:
        return (
            "Usage: /vision-bridge <image> [question]\n"
            "Runs SmolVLM first, releases it, then gives the saved visual report to Moondream2. "
            "No HTML or DeepSeek-Coder stage is used."
        )
    parser = make_parser()
    argv = [values[0]]
    if len(values) > 1:
        argv.extend(["--question", values[1]])
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return "Usage: /vision-bridge <image> [question]"
    return run_bridge(args)


def main() -> int:
    print(run_bridge(make_parser().parse_args()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
