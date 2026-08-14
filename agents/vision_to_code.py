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
from time import monotonic
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    from PIL import Image
except ImportError:  # Pillow is optional on Termux; the pipeline falls back safely.
    Image = None


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

CODE_PROMPT_TEMPLATE = """Create one complete standalone {target} document from the visual specification below.
Use semantic, responsive markup and embed CSS in a single style block. Do not use external dependencies.
Return only source code. Do not use Markdown fences, explanations, examples, or additional sections.
Finish immediately after the closing document tag.

VISUAL SPECIFICATION:
{visual_spec}
"""

HTML_SHELL_PREFIX = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <style>
    :root { color-scheme: light; font-family: system-ui, sans-serif; }
    body { margin: 0; min-height: 100vh; background: #f4f6f8; color: #18212b; }
    main { box-sizing: border-box; display: grid; place-items: center; min-height: 100vh; padding: 24px; }
    section, article, form { box-sizing: border-box; width: min(100%, 440px); padding: 24px; background: #fff; border: 1px solid #dce2e8; border-radius: 16px; box-shadow: 0 10px 28px rgba(24, 33, 43, .08); }
    h1, h2, p { margin-top: 0; }
    button, input, textarea { box-sizing: border-box; width: 100%; min-height: 42px; margin-top: 10px; padding: 10px 12px; border: 1px solid #b9c4cf; border-radius: 8px; font: inherit; }
    button { cursor: pointer; border: 0; background: #1463d8; color: #fff; font-weight: 650; }
  </style>
</head>
<body>
"""

HTML_SHELL_SUFFIX = "\n</body>\n</html>\n"


@dataclass(frozen=True)
class ImagePreparation:
    path: Path
    summary: str


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
    projector_offload: str = "auto",
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
        "128",
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
        "--temp",
        "0.1",
        "--image-max-tokens",
        str(image_max_tokens),
        "--perf",
    ]
    if projector_offload == "on":
        command.append("--mmproj-offload")
    elif projector_offload == "off":
        command.append("--no-mmproj-offload")
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
        "512",
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


def _extract_generated_source(text: str, output_path: Path) -> str:
    """Recover source emitted on either stream by llama-cli's terminal-oriented build."""
    source = text.split("SOLUTION:", 1)[-1] if "SOLUTION:" in text else text
    html_match = re.search(r"<\|im_start\|>html\s*(.*?)\s*<\|im_end\|>", source, flags=re.DOTALL | re.IGNORECASE)
    css_match = re.search(r"<\|im_start\|>css\s*(.*?)\s*<\|im_end\|>", source, flags=re.DOTALL | re.IGNORECASE)
    if html_match:
        html_fragment = html_match.group(1).strip()
        css = css_match.group(1).strip() if css_match else ""
        if output_path.suffix.lower() in {".html", ".htm"} and css:
            return (
                "<!doctype html>\n<html lang=\"en\">\n<head>\n"
                "  <meta charset=\"utf-8\">\n"
                "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
                "  <style>\n" + css + "\n  </style>\n</head>\n<body>\n"
                + html_fragment + "\n</body>\n</html>\n"
            )
        if output_path.suffix.lower() in {".html", ".htm"} and re.fullmatch(r"(?is)<main\b[^>]*>.*</main>", html_fragment):
            return HTML_SHELL_PREFIX + html_fragment + HTML_SHELL_SUFFIX
        return html_fragment + "\n"

    html_document = re.search(r"(?is)(<!doctype html.*?</html>|<html.*?</html>)", source)
    if html_document:
        return html_document.group(1).strip() + "\n"

    main_fragment = re.search(r"(?is)(<main\b[^>]*>.*?</main>)", source)
    if main_fragment:
        return HTML_SHELL_PREFIX + main_fragment.group(1).strip() + HTML_SHELL_SUFFIX

    fenced_documents = re.findall(r"```(?:html|\w+)?\s*(.*?)\s*```", source, flags=re.DOTALL | re.IGNORECASE)
    for document in fenced_documents:
        fragment = re.search(r"(?is)(<main\b[^>]*>.*?</main>)", document)
        if fragment:
            return HTML_SHELL_PREFIX + fragment.group(1).strip() + HTML_SHELL_SUFFIX
        if document.strip():
            return document.strip() + "\n"
    return ""


def _run_stage(
    command: list[str],
    timeout: int,
    log_path: Path,
    label: str,
    live_output: bool = False,
    stop_after: str | None = None,
) -> tuple[int, str, str]:
    """Run one model stage, optionally mirroring progress while retaining a complete log."""
    if live_output:
        output_parts: list[str] = []
        completion_seen = threading.Event()
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
                    if stop_after and stop_after.lower() in line.lower() and not completion_seen.is_set():
                        completion_seen.set()
                        process.terminate()

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

        if completion_seen.is_set():
            return_code = 0
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


def _prepare_image(
    source: Path,
    work_dir: Path,
    max_long_edge: int,
    jpeg_quality: int,
    enabled: bool,
) -> ImagePreparation:
    """Create a deterministic smaller JPEG for vision inference when useful."""
    if not enabled:
        return ImagePreparation(source, "preprocessing disabled; original image used")
    if Image is None:
        return ImagePreparation(source, "Pillow unavailable; original image used")
    try:
        work_dir.mkdir(parents=True, exist_ok=True)
        with Image.open(source) as opened:
            original_width, original_height = opened.size
            longest = max(original_width, original_height)
            scale = min(1.0, max_long_edge / longest) if longest else 1.0
            target_width = max(1, round(original_width * scale))
            target_height = max(1, round(original_height * scale))
            image = opened.convert("RGB")
            if (target_width, target_height) != image.size:
                resampling = getattr(Image, "Resampling", Image).LANCZOS
                image = image.resize((target_width, target_height), resampling)
            prepared = work_dir / "prepared_visual_input.jpg"
            image.save(prepared, "JPEG", quality=jpeg_quality, optimize=True)
    except (OSError, ValueError) as exc:
        return ImagePreparation(source, f"preprocessing skipped ({exc}); original image used")

    original_bytes = source.stat().st_size
    prepared_bytes = prepared.stat().st_size
    action = "resized" if scale < 1.0 else "re-encoded"
    return ImagePreparation(
        prepared,
        (
            f"{action} {original_width}x{original_height} to {target_width}x{target_height}; "
            f"{original_bytes // 1024} KiB to {prepared_bytes // 1024} KiB JPEG"
        ),
    )


def _format_seconds(seconds: float) -> str:
    return f"{seconds:.1f}s"


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

    preparation_started = monotonic()
    prepared_image = _prepare_image(
        image,
        paths.work_dir,
        args.max_image_edge,
        args.jpeg_quality,
        not args.no_preprocess,
    )
    preparation_seconds = monotonic() - preparation_started

    vision_command = build_vision_command(
        mtmd_cli,
        vision_model,
        mmproj,
        prepared_image.path,
        context=args.context,
        batch=args.batch,
        ubatch=args.ubatch,
        image_max_tokens=args.image_max_tokens,
        projector_offload=args.projector_offload,
    )
    coder_command = build_coder_command(llama_cli, coder_model, paths.coder_prompt, paths.output)

    if args.dry_run:
        return (
            "Dry run: SmolVLM and DeepSeek-Coder would run sequentially.\n\n"
            f"Vision command:\n{_stage_command_string(vision_command)}\n\n"
            f"Coder command:\n{_stage_command_string(coder_command)}\n\n"
            f"Work directory: {paths.work_dir}"
        )

    print(f"Image preparation: {prepared_image.summary} ({_format_seconds(preparation_seconds)})", flush=True)
    print(f"Projector offload preference: {args.projector_offload}", flush=True)
    print("Starting SmolVLM visual stage. Live image-encoding progress will appear below; do not interrupt it while batches advance.", flush=True)
    vision_started = monotonic()
    visual_status, _visual_stdout, visual_output = _run_stage(
        vision_command,
        args.vision_timeout,
        paths.visual_log,
        "SmolVLM vision stage",
        live_output=True,
    )
    vision_seconds = monotonic() - vision_started
    if visual_status != 0:
        return (
            f"SmolVLM stage failed with exit code {visual_status} after {_format_seconds(vision_seconds)}. "
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

    print(f"SmolVLM completed in {_format_seconds(vision_seconds)}. Starting DeepSeek-Coder after releasing the vision process.", flush=True)
    coder_started = monotonic()
    coder_status, coder_stdout, coder_output = _run_stage(
        coder_command,
        args.coder_timeout,
        paths.coder_log,
        "DeepSeek-Coder stage",
        live_output=True,
        stop_after="</html>" if paths.output.suffix.lower() in {".html", ".htm"} else None,
    )
    coder_seconds = monotonic() - coder_started
    generated_source = _extract_generated_source(coder_stdout or coder_output, paths.output)
    if coder_status != 0 and not generated_source:
        return (
            f"DeepSeek-Coder stage failed with exit code {coder_status} after {_format_seconds(coder_seconds)}. "
            f"Visual spec remains at: {paths.visual_spec}\n"
            f"Coder log: {paths.coder_log}\n\n{_tail(coder_output)}"
        )
    if not generated_source:
        return (
            "DeepSeek-Coder completed but did not emit extractable source code. "
            f"Visual spec remains at: {paths.visual_spec}\n"
            f"Coder log: {paths.coder_log}"
        )

    paths.output.parent.mkdir(parents=True, exist_ok=True)
    paths.output.write_text(generated_source, encoding="utf-8")
    completion_note = "Visual-to-code pipeline completed sequentially."
    if coder_status != 0:
        completion_note = (
            f"DeepSeek-Coder was stopped after {_format_seconds(coder_seconds)}, but a complete source document was salvaged."
        )
    return (
        completion_note + "\n"
        f"Prepared image: {prepared_image.path} ({prepared_image.summary})\n"
        f"Visual specification: {paths.visual_spec}\n"
        f"Generated {args.target}: {paths.output}\n"
        f"Timing: preparation={_format_seconds(preparation_seconds)}, vision={_format_seconds(vision_seconds)}, coder={_format_seconds(coder_seconds)}\n"
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
    parser.add_argument("--max-image-edge", type=int, default=1280, help="Resize the longest image edge before vision inference")
    parser.add_argument("--jpeg-quality", type=int, default=80, help="JPEG quality for the prepared vision image")
    parser.add_argument("--no-preprocess", action="store_true", help="Use the original image without resize or JPEG compression")
    parser.add_argument("--projector-offload", choices=("auto", "on", "off"), default="auto", help="Multimodal projector offload preference; auto leaves the local CLI default unchanged")
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
