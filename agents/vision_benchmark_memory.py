#!/usr/bin/env python3
"""Durable paired-vision benchmark memory for Lorna2.

The module only parses completed benchmark artifacts.  It never starts a model.
"""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENT_DIR = Path(__file__).resolve().parent
MEMORY_PATH = AGENT_DIR / "benchmark_memory.json"
DEFAULT_TIMEOUT_SECONDS = 180
PAIR_BY_LABEL = {
    "moondream2": "moondream_2025",
    "smolvlm": "smolvlm",
}
SUMMARY_ROW = re.compile(
    r"^\s*(?P<model>Moondream2|SmolVLM)\s*\|\s*"
    r"(?P<label>[^|]+?)\s*\|\s*"
    r"t=(?P<threads>\d+)\s+tb=(?P<batch_threads>\d+)\s+"
    r"n=(?P<output_tokens>\d+)\s+image=(?P<image_tokens>[^|\s]+)\s*\|\s*"
    r"exit=(?P<exit_code>-?\d+)\s*\|\s*"
    r"elapsed=(?P<elapsed_s>\d+(?:\.\d+)?)s\s*\|\s*"
    r"log=(?P<log_path>.+?)\s*$"
)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ensure_memory(memory: dict[str, Any]) -> dict[str, Any]:
    """Add only the fields owned by this module; preserve prior benchmark memory."""
    memory.setdefault("schema_version", 1)
    memory["schema_version"] = max(3, int(memory["schema_version"]))
    memory.setdefault("device", {})
    memory.setdefault("workflow_rules", [])
    memory.setdefault("known_models", {})
    memory.setdefault("runs", [])
    memory.setdefault("recommendations", {})
    memory.setdefault("vision_runs", [])
    memory.setdefault("vision_recommendations", {})
    return memory


def load_memory(path: Path = MEMORY_PATH) -> dict[str, Any]:
    try:
        memory = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        memory = {}
    return _ensure_memory(memory)


def save_memory(memory: dict[str, Any], path: Path = MEMORY_PATH) -> None:
    """Commit memory atomically so an interrupted benchmark cannot corrupt it."""
    memory = _ensure_memory(memory)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(memory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _read_timeout_and_mode(summary_path: Path) -> tuple[int, bool]:
    timeout = DEFAULT_TIMEOUT_SECONDS
    dry_run = False
    try:
        header = summary_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return timeout, dry_run
    match = re.search(r"^timeout=(\d+)s\s+per\s+model\s*$", header, re.MULTILINE)
    if match:
        timeout = int(match.group(1))
    dry_run = bool(re.search(r"^mode=dry-run\s*$", header, re.MULTILINE))
    return timeout, dry_run


def _response_from_log(log_path: Path) -> tuple[bool, str]:
    """Return whether the image encoding completed and the concise model response."""
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False, ""

    lines = text.splitlines()

    def is_encoding_complete(line: str) -> bool:
        normalized = line.lower()
        return (
            "encoding mtmd batch done" in normalized
            or "mtmd batch encoding done" in normalized
        )

    encoding_done = any(is_encoding_complete(line) for line in lines)
    last_encoding = -1
    for index, line in enumerate(lines):
        if is_encoding_complete(line):
            last_encoding = index
    if last_encoding < 0:
        return encoding_done, ""

    response_lines: list[str] = []
    runtime_line = re.compile(r"^\s*\d+\.\d+\.\d+\s+[IWE]\s+")
    for raw in lines[last_encoding + 1:]:
        line = raw.strip()
        lower = line.lower()
        if not line:
            continue
        if runtime_line.match(line) or lower.startswith(("llama_perf", "timings", "sampling:", "sampler ")):
            continue
        if lower.startswith(("[ prompt:", "[prompt:", "[ generation:", "[generation:")):
            continue
        if line.startswith(("<|", "user:", "assistant:")):
            continue
        response_lines.append(line)

    response = "\n".join(response_lines).strip()
    return encoding_done, response[:2000]


def _run_id(summary_path: Path, row_number: int, raw_row: str) -> str:
    digest = hashlib.sha256(f"{summary_path.resolve()}|{row_number}|{raw_row}".encode("utf-8")).hexdigest()
    return f"vision-{digest[:16]}"


def parse_summary(summary_path: str | Path) -> list[dict[str, Any]]:
    """Parse a benchmark summary.txt without changing any model or benchmark state."""
    path = Path(summary_path).expanduser()
    if path.is_dir():
        path = path / "summary.txt"
    if not path.is_file():
        raise FileNotFoundError(f"Vision benchmark summary not found: {path}")

    timeout_seconds, dry_run = _read_timeout_and_mode(path)
    records: list[dict[str, Any]] = []
    for row_number, raw_line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        match = SUMMARY_ROW.match(raw_line)
        if not match:
            continue
        values = match.groupdict()
        model_pair = PAIR_BY_LABEL[values["model"].lower()]
        log_path = Path(values["log_path"]).expanduser()
        encoding_done, response_text = _response_from_log(log_path)
        elapsed_s = float(values["elapsed_s"])
        exit_code = int(values["exit_code"])
        completed_successfully = (not dry_run) and exit_code == 0 and elapsed_s < timeout_seconds
        records.append(
            {
                "run_id": _run_id(path, row_number, raw_line),
                "model_pair": model_pair,
                "model_label": values["model"],
                "label": values["label"].strip(),
                "config": {
                    "threads": int(values["threads"]),
                    "batch_threads": int(values["batch_threads"]),
                    "output_tokens": int(values["output_tokens"]),
                    "image_tokens": values["image_tokens"],
                },
                "elapsed_s": elapsed_s,
                "exit_code": exit_code,
                "encoding_done": encoding_done,
                "response_text": response_text,
                "completed_successfully": completed_successfully,
                "timestamp": now_iso(),
                "source_summary": str(path),
                "source_log": str(log_path),
                "timeout_seconds": timeout_seconds,
                "dry_run": dry_run,
            }
        )
    return records


def _refresh_recommendations(memory: dict[str, Any]) -> None:
    """Select the quickest actual encoded run per model pair; leave historical runs intact."""
    recommendations: dict[str, dict[str, Any]] = {}
    for pair in sorted(PAIR_BY_LABEL.values()):
        eligible = [
            run for run in memory["vision_runs"]
            if run.get("model_pair") == pair
            and run.get("completed_successfully")
            and run.get("encoding_done")
        ]
        if not eligible:
            continue
        best = min(eligible, key=lambda run: (float(run.get("elapsed_s", float("inf"))), run.get("timestamp", "")))
        recommendations[pair] = {
            "model_pair": pair,
            "run_id": best["run_id"],
            "config": deepcopy(best["config"]),
            "elapsed_s": best["elapsed_s"],
            "timestamp": best["timestamp"],
            "source_summary": best["source_summary"],
            "reason": "Lowest elapsed successful run with image encoding confirmed.",
        }
    memory["vision_recommendations"] = recommendations


def ingest(summary_path: str | Path, memory_path: Path = MEMORY_PATH) -> tuple[int, int]:
    """Persist any new rows from one vision benchmark directory and refresh profiles."""
    records = parse_summary(summary_path)
    memory = load_memory(memory_path)
    known = {str(run.get("run_id", "")) for run in memory["vision_runs"]}
    new_records = [record for record in records if record["run_id"] not in known]
    memory["vision_runs"].extend(new_records)
    _refresh_recommendations(memory)
    save_memory(memory, memory_path)
    return len(new_records), len(records)


def _format_config(config: dict[str, Any]) -> str:
    return "t={threads} tb={batch_threads} n={output_tokens} image={image_tokens}".format(**config)


def format_results(argument: str = "", memory_path: Path = MEMORY_PATH) -> str:
    """Show recent stored results without launching models or re-reading logs."""
    memory = load_memory(memory_path)
    tokens = shlex.split(argument) if argument.strip() else []
    pair_filter = ""
    limit = 8
    if tokens:
        if tokens[0] in PAIR_BY_LABEL.values():
            pair_filter = tokens.pop(0)
        elif tokens[0].isdigit():
            limit = max(1, min(50, int(tokens.pop(0))))
        else:
            return "Usage: /vision-results [moondream_2025|smolvlm] [count]"
    if tokens:
        if tokens[0].isdigit():
            limit = max(1, min(50, int(tokens.pop(0))))
        else:
            return "Usage: /vision-results [moondream_2025|smolvlm] [count]"
    if tokens:
        return "Usage: /vision-results [moondream_2025|smolvlm] [count]"

    runs = list(reversed(memory["vision_runs"]))
    if pair_filter:
        runs = [run for run in runs if run.get("model_pair") == pair_filter]
    runs = runs[:limit]
    if not runs:
        return "No persisted vision benchmark runs yet. Run 'lorna vision-bench' or use /vision-ingest <benchmark-directory>."

    lines = ["Lorna2 persisted vision benchmark results:"]
    for run in runs:
        result = "OK" if run.get("completed_successfully") else f"exit={run.get('exit_code')}"
        encoded = "encoded" if run.get("encoding_done") else "no-encoding-confirmation"
        lines.append(
            f"  {run.get('model_pair')} [{run.get('label')}]: {_format_config(run['config'])} | "
            f"{run.get('elapsed_s')}s | {result} | {encoded}"
        )
    return "\n".join(lines)


def format_profile(argument: str = "", memory_path: Path = MEMORY_PATH) -> str:
    """Show recommended configurations sourced only from recorded successful runs."""
    requested = argument.strip() or "all"
    if requested not in {"all", *PAIR_BY_LABEL.values()}:
        return "Usage: /vision-profile [moondream_2025|smolvlm]"
    recommendations = load_memory(memory_path)["vision_recommendations"]
    pairs = list(PAIR_BY_LABEL.values()) if requested == "all" else [requested]
    lines = ["Lorna2 recommended vision profiles:"]
    for pair in pairs:
        recommendation = recommendations.get(pair)
        if not recommendation:
            lines.append(f"  {pair}: no successful encoded run stored yet.")
            continue
        lines.append(
            f"  {pair}: {_format_config(recommendation['config'])} | "
            f"{recommendation['elapsed_s']}s | {recommendation['reason']}"
        )
    return "\n".join(lines)


def command(argument: str = "") -> str:
    """Lorna2 command dispatcher for /vision-results, /vision-profile, and /vision-ingest."""
    try:
        parts = shlex.split(argument)
    except ValueError as exc:
        return f"Invalid vision benchmark command: {exc}"
    if not parts or parts[0].lower() in {"help", "--help", "-h"}:
        return (
            "Vision benchmark memory:\n"
            "  /vision-results [moondream_2025|smolvlm] [count]\n"
            "  /vision-profile [moondream_2025|smolvlm]\n"
            "  /vision-ingest <benchmark-output-directory|summary.txt>\n"
            "Ingestion only parses saved artifacts; it never launches a model."
        )
    action = parts[0].lower()
    if action in {"results", "recent"}:
        return format_results(" ".join(parts[1:]))
    if action in {"profile", "profiles"}:
        return format_profile(" ".join(parts[1:]))
    if action == "ingest":
        if len(parts) != 2:
            return "Usage: /vision-ingest <benchmark-output-directory|summary.txt>"
        try:
            added, parsed = ingest(parts[1])
        except (OSError, ValueError, FileNotFoundError) as exc:
            return f"Vision benchmark ingestion failed: {exc}"
        return f"Vision benchmark ingestion complete: {added} new row(s) stored from {parsed} parsed row(s).\n{format_profile()}"
    return "Usage: /vision-results | /vision-profile | /vision-ingest <benchmark-output-directory|summary.txt>"


def main() -> int:
    if len(sys.argv) < 2:
        print(command("help"))
        return 0
    action = sys.argv[1].lower()
    if action == "ingest" and len(sys.argv) == 3:
        try:
            added, parsed = ingest(sys.argv[2])
        except (OSError, ValueError, FileNotFoundError) as exc:
            print(f"Vision benchmark ingestion failed: {exc}", file=sys.stderr)
            return 1
        print(f"Vision benchmark ingestion complete: {added} new row(s) stored from {parsed} parsed row(s).")
        return 0
    if action == "results":
        print(format_results(" ".join(sys.argv[2:])))
        return 0
    if action in {"profile", "profiles"}:
        print(format_profile(" ".join(sys.argv[2:])))
        return 0
    print(command("help"))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
