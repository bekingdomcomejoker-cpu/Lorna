#!/usr/bin/env python3
"""Sequential, low-memory visual-specification-to-code pipeline for Lorna2.

SmolVLM is loaded first with llama-mtmd-cli and is fully released before
DeepSeek-Coder is started with llama-cli.  The stages never coexist in memory.
"""

from __future__ import annotations

import argparse
import re
import shlex
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


HOME = Path.home()
AGENT_DIR = Path(__file__).resolve().parent
DEFAULT_VISION_MODEL = HOME / "models" / "SmolVLM-256M-Instruct-Q4_K_M.gguf"
DEFAULT_MMPROJ = HOME / "models" / "mmproj-SmolVLM-256M-Instruct-f16.gguf"
DEFAULT_CODER_MODEL = HOME / "models" / "deepseek-coder-1.3b-instruct-q4_k_m.gguf"
DEFAULT_WORK_DIR = HOME / ".lorna_v2" / "visual_to_code"
VISUAL_SPEC_GRAMMAR = AGENT_DIR / "visual_spec.gbnf"

VISION_SYSTEM_PROMPT = """You are a precise visual interface analyst. Describe only what is visible in the supplied image. Never invent text, controls, colors, or layout details."""

VISUAL_SPEC_PROMPT = """Analyze the supplied image for code reconstruction. Return exactly this compact specification:
BEGIN_VISUAL_SPEC
layout: top-to-bottom sections and hierarchy
elements: visible controls, cards, images, labels, or keyboard
style: colors, spacing, typography, borders, and alignment
text: visible text, or [unreadable]
END_VISUAL_SPEC"""

CODE_PROMPT_TEMPLATE = """Create a complete {target} implementation from the visual specification below.
Use semantic, responsive markup and avoid external dependencies unless the specification requires them.
Return only the complete source code; do not add an explanation or Markdown fences.

VISUAL SPECIFICATION:
{visual_spec}
"""


@dataclass(frozen=True)
class PipelinePaths:
    work_dir: Path
    visual_log: Path
    visual_spec: Path
    coder_prompt: Path
    coder_log: Path
    output: Path


def _which(name: str) -> str | None:
    return shutil.which(name)


def _help_contains(binary: str, option: str) -> bool:
    try:
        result = subprocess.run(
            [binary, "--help"], capture_output=True, text=True, timeout=15, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return option in (result.stdout + result.stderr)


def _is_ollama_running() -> bool:
    try:
        result = subprocess.run(
            ["pgrep", "-f", "[o]llama serve"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _tail(text: str, lines: int = 18) -> str:
    selected = text.strip().splitlines()[-lines:]
    return "\n".join(selected)


def _stage_command_string(command: Iterable[str]) -> str:
    return shlex.join([str(item) for item in command])


def build_vision_command(
    mtmd_cli: str,
    model: Path,
    mmproj: Path,
    image: Path,
    context: int = 2048,
    batch: int = 8,
    ubatch: int = 8,
    image_max_tokens: int = 128,
) -> list[str]:
    """Build the standalone SmolVLM stage without launching it."""
    command = [
        mtmd_cli,
        "-m",
        str(model),
        "--mmproj",
        str(mmproj),
        "--image",
        str(image),
        "-sys",
        VISION_SYSTEM_PROMPT,
        "-p",
        VISUAL_SPEC_PROMPT,
        "--grammar-file",
        str(VISUAL_SPEC_GRAMMAR),
        "--no-jinja",
        "--chat-template",
        "smolvlm",
        "-n",
        "256",
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
        "--temp",
        "0.1",
        "--image-max-tokens",
        str(image_max_tokens),
        "--perf",
    ]
    return command


def build_coder_command(
    llama_cli: str,
    model: Path,
    prompt_file: Path,
    output_file: Path,
) -> list[str]:
    """Build the direct DeepSeek-Coder stage without launching it."""
    command = [
        llama_cli,
        "-m",
        str(model),
        "-f",
        str(prompt_file),
        "-n",
        "768",
        "-c",
        "1024",
        "-t",
        "3",
        "-b",
        "32",
        "--temp",
        "0.2",
    ]
    if _help_contains(llama_cli, "--single-turn"):
        command.append("--single-turn")
    if _help_contains(llama_cli, "--no-display-prompt"):
        command.append("--no-display-prompt")
    if _help_contains(llama_cli, "--no-perf"):
        command.append("--no-perf")
    if _help_contains(llama_cli, "--log-disable"):
        command.append("--log-disable")
    return command


def _strip_stage_logs(text: str) -> str:
    """Extract only the bounded visual specification from mixed mtmd CLI output."""
    match = re.search(r"BEGIN_VISUAL_SPEC\s*(.*?)\s*END_VISUAL_SPEC", text, flags=re.DOTALL)
    if not match:
        return ""
    content = match.group(1).strip()
    # Remove a timestamped mtmd prefix if a model emits markers on logged lines.
    content = re.sub(r"(?m)^\d+\.\d+\.\d+\s+[A-Z]\s+", "", content)
    return content.strip()


def _run_stage(
    command: list[str], timeout: int, log_path: Path, label: str, live_output: bool = False
) -> tuple[int, str, str]:
    """Run one model stage, optionally mirroring progress while retaining a complete log."""
    if live_output:
        output_parts: list[str] = []
        log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            combined = f"Could not start {label}: {exc}"
            log_path.write_text(combined, encoding="utf-8")
            return 127, "", combined

        def mirror_output() -> None:
            assert process.stdout is not None
            with log_path.open("w", encoding="utf-8") as log_file:
                for line in iter(process.stdout.readline, ""):
                    output_parts.append(line)
                    log_file.write(line)
                    log_file.flush()
                    print(line, end="", flush=True)

        reader = threading.Thread(target=mirror_output, daemon=True)
        reader.start()
        try:
            return_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            message = f"\n{label} timed out after {timeout}s and was stopped.\n"
            output_parts.append(message)
            with log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(message)
            return_code = 124
        except KeyboardInterrupt:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            message = f"\n{label} was cancelled by the user; DeepSeek-Coder was not started.\n"
            output_parts.append(message)
            with log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(message)
            return_code = 130
        finally:
            if process.stdout is not None:
                process.stdout.close()
            reader.join(timeout=2)

        combined = "".join(output_parts)
        return return_code, combined, combined

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        combined = f"{stdout}\n{stderr}\n{label} timed out after {timeout}s."
        log_path.write_text(combined, encoding="utf-8")
        return 124, stdout, combined
    except KeyboardInterrupt:
        combined = f"{label} was cancelled by the user."
        log_path.write_text(combined, encoding="utf-8")
        return 130, "", combined
    except OSError as exc:
        combined = f"Could not start {label}: {exc}"
        log_path.write_text(combined, encoding="utf-8")
        return 127, "", combined

    stdout = result.stdout or ""
    stderr = result.stderr or ""
    combined = stdout + stderr
    log_path.write_text(combined, encoding="utf-8")
    return result.returncode, stdout, combined


def _paths(work_dir: Path, output: Path | None) -> PipelinePaths:
    work_dir.mkdir(parents=True, exist_ok=True)
    final_output = output if output is not None else work_dir / "generated_page.html"
    return PipelinePaths(
        work_dir=work_dir,
        visual_log=work_dir / "smolvlm_run.log",
        visual_spec=work_dir / "visual_spec.md",
        coder_prompt=work_dir / "deepseek_coder_prompt.txt",
        coder_log=work_dir / "deepseek_coder_run.log",
        output=final_output,
    )


def _validate_paths(paths: Iterable[Path]) -> list[str]:
    missing = [str(path) for path in paths if not path.is_file()]
    return missing


def run_pipeline(args: argparse.Namespace) -> str:
    image = Path(args.image).expanduser().resolve()
    vision_model = Path(args.vision_model).expanduser().resolve()
    mmproj = Path(args.mmproj).expanduser().resolve()
    coder_model = Path(args.coder_model).expanduser().resolve()
    work_dir = Path(args.work_dir).expanduser().resolve()
    output = Path(args.output).expanduser().resolve() if args.output else None
    paths = _paths(work_dir, output)

    mtmd_cli = _which("llama-mtmd-cli")
    llama_cli = _which("llama-cli")
    if not mtmd_cli or not llama_cli:
        return "Visual pipeline unavailable: both llama-mtmd-cli and llama-cli must be installed."

    missing = _validate_paths([image, vision_model, mmproj, coder_model])
    if missing:
        return "Visual pipeline stopped; missing required file(s):\n  " + "\n  ".join(missing)

    if _is_ollama_running() and not args.allow_ollama:
        return (
            "Visual pipeline stopped before loading models because `ollama serve` is running. "
            "Stop Ollama first to free memory, then rerun. Use --allow-ollama only if you accept "
            "higher memory pressure."
        )

    vision_command = build_vision_command(
        mtmd_cli,
        vision_model,
        mmproj,
        image,
        context=args.context,
        batch=args.batch,
        ubatch=args.ubatch,
        image_max_tokens=args.image_max_tokens,
    )
    coder_command = build_coder_command(llama_cli, coder_model, paths.coder_prompt, paths.output)

    if args.dry_run:
        return (
            "Dry run: SmolVLM and DeepSeek-Coder would run sequentially.\n\n"
            f"Vision command:\n{_stage_command_string(vision_command)}\n\n"
            f"Coder command:\n{_stage_command_string(coder_command)}\n\n"
            f"Work directory: {paths.work_dir}"
        )

    print("Starting SmolVLM visual stage. Live image-encoding progress will appear below; do not interrupt it while batches advance.", flush=True)
    visual_status, _visual_stdout, visual_output = _run_stage(
        vision_command,
        args.vision_timeout,
        paths.visual_log,
        "SmolVLM vision stage",
        live_output=True,
    )
    if visual_status != 0:
        return (
            f"SmolVLM stage failed with exit code {visual_status}. "
            f"Log: {paths.visual_log}\n\n{_tail(visual_output)}"
        )

    visual_spec = _strip_stage_logs(visual_output)
    if not visual_spec:
        return (
            "SmolVLM completed but did not return the required BEGIN_VISUAL_SPEC/END_VISUAL_SPEC block. "
            f"No code model was started. Inspect: {paths.visual_log}"
        )
    paths.visual_spec.write_text(visual_spec + "\n", encoding="utf-8")

    coder_prompt = CODE_PROMPT_TEMPLATE.format(target=args.target, visual_spec=visual_spec)
    paths.coder_prompt.write_text(coder_prompt, encoding="utf-8")

    print("SmolVLM completed. Starting DeepSeek-Coder after releasing the vision process.", flush=True)
    coder_status, coder_stdout, coder_output = _run_stage(
        coder_command, args.coder_timeout, paths.coder_log, "DeepSeek-Coder stage"
    )
    if coder_status != 0:
        return (
            f"DeepSeek-Coder stage failed with exit code {coder_status}. "
            f"Visual spec remains at: {paths.visual_spec}\n"
            f"Coder log: {paths.coder_log}\n\n{_tail(coder_output)}"
        )
    if not coder_stdout.strip():
        return (
            "DeepSeek-Coder completed without source output. "
            f"Visual spec remains at: {paths.visual_spec}\n"
            f"Coder log: {paths.coder_log}"
        )

    paths.output.parent.mkdir(parents=True, exist_ok=True)
    paths.output.write_text(coder_stdout.strip() + "\n", encoding="utf-8")
    return (
        "Visual-to-code pipeline completed sequentially.\n"
        f"Visual specification: {paths.visual_spec}\n"
        f"Generated {args.target}: {paths.output}\n"
        f"Stage logs: {paths.visual_log} and {paths.coder_log}"
    )


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run SmolVLM visual preprocessing, then DeepSeek-Coder after SmolVLM exits."
    )
    parser.add_argument("image", help="Local image or screenshot to inspect")
    parser.add_argument("--output", help="Output source file (default: ~/.lorna_v2/visual_to_code/generated_page.html)")
    parser.add_argument("--target", default="responsive HTML and CSS", help="Desired generated-code target")
    parser.add_argument("--vision-model", default=str(DEFAULT_VISION_MODEL))
    parser.add_argument("--mmproj", default=str(DEFAULT_MMPROJ))
    parser.add_argument("--coder-model", default=str(DEFAULT_CODER_MODEL))
    parser.add_argument("--work-dir", default=str(DEFAULT_WORK_DIR))
    parser.add_argument("--context", type=int, default=2048)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--ubatch", type=int, default=8)
    parser.add_argument("--image-max-tokens", type=int, default=128)
    parser.add_argument("--vision-timeout", type=int, default=240)
    parser.add_argument("--coder-timeout", type=int, default=300)
    parser.add_argument("--allow-ollama", action="store_true", help="Allow the pipeline to run while ollama serve is active")
    parser.add_argument("--dry-run", action="store_true", help="Print the sequential commands without launching models")
    return parser


def command(argument: str) -> str:
    """Lorna2 command adapter: /visual-code <image> [output-file]."""
    try:
        values = shlex.split(argument)
    except ValueError as exc:
        return f"Invalid /visual-code arguments: {exc}"
    if not values or values[0] in {"help", "--help", "-h"}:
        return (
            "Usage: /visual-code <image> [output-file]\n"
            "Runs SmolVLM first, saves a visual specification, releases it, then runs DeepSeek-Coder. "
            "Stop `ollama serve` first for best memory headroom."
        )
    parser = make_parser()
    argv = [values[0]]
    if len(values) > 1:
        argv.extend(["--output", values[1]])
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return "Usage: /visual-code <image> [output-file]"
    return run_pipeline(args)


def main() -> int:
    args = make_parser().parse_args()
    print(run_pipeline(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
