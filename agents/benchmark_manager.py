#!/usr/bin/env python3
"""Durable, resource-aware benchmark orchestration for Lorna2 Agent."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENT_DIR = Path(__file__).resolve().parent
LORNA_DIR = AGENT_DIR.parent
MEMORY_PATH = AGENT_DIR / "benchmark_memory.json"
MODELS_DIR = Path.home() / "models"
DEFAULT_PROMPT = "Explain the convergence of the p-series and relate it to the Riemann zeta function."
SAFE_SWEEP = {
    "contexts": [512, 1024],
    "threads": [2, 4],
    "batches": [32, 64],
    "temperature": 0.2,
    "tokens": 100,
    "timeout_seconds": 120,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_memory() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "device": {
            "label": "Redmi 13C / Helio G85 / Termux",
            "ram_mb": 3720,
            "notes": "Prefer sequential tests. Do not benchmark multiple models concurrently.",
        },
        "workflow_rules": [
            "Use only one llama-cli process at a time.",
            "Let a fixed token budget finish before the queued /exit is consumed.",
            "Abort or skip a run when the model file is corrupt or memory is critically low.",
            "Use elapsed throughput only when llama.cpp does not emit raw timing lines; label it EST.",
        ],
        "known_models": {
            "qwen2.5-0.5b-instruct-q4_k_m.gguf": {
                "status": "safe_candidate",
                "notes": "Observed interactive generation around 7.6 t/s in a user-captured Termux session; configuration was not recorded.",
            },
            "smollm2-360m-instruct-q4_k_m.gguf": {
                "status": "safe_candidate",
                "notes": "Observed interactive generation around 13.0 t/s in a user-captured Termux session; configuration was not recorded.",
            },
            "tinydolphin-2.8-1.1b-q4_k_m.gguf": {
                "status": "corrupt",
                "notes": "llama.cpp reported tensor data outside file bounds; do not tune until the GGUF is replaced.",
            },
        },
        "runs": [],
        "recommendations": {},
    }


def load_memory() -> dict[str, Any]:
    if not MEMORY_PATH.exists():
        memory = default_memory()
        save_memory(memory)
        return memory
    try:
        memory = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        memory = default_memory()
    for key, value in default_memory().items():
        memory.setdefault(key, value)
    return memory


def save_memory(memory: dict[str, Any]) -> None:
    temp = MEMORY_PATH.with_suffix(".json.tmp")
    temp.write_text(json.dumps(memory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(MEMORY_PATH)


def memory_mb() -> tuple[int, int]:
    available = total = 0
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            name, value, *_ = line.split()
            if name == "MemAvailable:":
                available = int(value) // 1024
            elif name == "MemTotal:":
                total = int(value) // 1024
    except OSError:
        pass
    return available, total


def swap_used_mb() -> int:
    total = free = 0
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            name, value, *_ = line.split()
            if name == "SwapTotal:":
                total = int(value)
            elif name == "SwapFree:":
                free = int(value)
    except OSError:
        pass
    return max(0, (total - free) // 1024)


def discover_models() -> list[Path]:
    if not MODELS_DIR.is_dir():
        return []
    return sorted(path for path in MODELS_DIR.glob("*.gguf") if path.stat().st_size > 50 * 1024 * 1024)


def resolve_model(query: str) -> Path | None:
    query = query.strip().lower()
    models = discover_models()
    if not query:
        return None
    aliases = {
        "qwen": "qwen2.5-0.5b-instruct-q4_k_m.gguf",
        "smollm": "smollm2-360m-instruct-q4_k_m.gguf",
        "smol": "smollm2-360m-instruct-q4_k_m.gguf",
        "tinydolphin": "tinydolphin-2.8-1.1b-q4_k_m.gguf",
    }
    target = aliases.get(query, query)
    for path in models:
        if path.name.lower() == target:
            return path
    matches = [path for path in models if target in path.name.lower()]
    return matches[0] if len(matches) == 1 else None


def llama_binary() -> str | None:
    return shutil.which("llama-cli")


def parse_raw_tps(text: str) -> tuple[str | None, str | None]:
    prompt = re.findall(r"Prompt:\s*([0-9]+(?:\.[0-9]+)?)\s*t/s", text, flags=re.I)
    generation = re.findall(r"Generation:\s*([0-9]+(?:\.[0-9]+)?)\s*t/s", text, flags=re.I)
    if not prompt:
        prompt = re.findall(r"prompt eval time.*?([0-9]+(?:\.[0-9]+)?)\s+tokens per second", text, flags=re.I)
    if not generation:
        generation = re.findall(r"(?:^|[^p])eval time.*?([0-9]+(?:\.[0-9]+)?)\s+tokens per second", text, flags=re.I | re.M)
    return (prompt[-1] if prompt else None, generation[-1] if generation else None)


def classify_failure(text: str, returncode: int) -> str:
    lowered = text.lower()
    if "corrupted or incomplete" in lowered or "not within the file bounds" in lowered:
        return "CORRUPT"
    if returncode == 124:
        return "TIMEOUT"
    return f"ERROR({returncode})"


def run_configuration(model: Path, ctx: int, threads: int, batch: int, temperature: float) -> dict[str, Any]:
    binary = llama_binary()
    if not binary:
        return {"status": "ERROR(no_llama_cli)"}
    with tempfile.TemporaryDirectory(prefix="lorna2_benchmark_") as temp_dir:
        prompt_file = Path(temp_dir) / "prompt.txt"
        prompt_file.write_text(DEFAULT_PROMPT + "\n", encoding="utf-8")
        command = [
            binary, "-m", str(model), "-f", str(prompt_file), "-n", str(SAFE_SWEEP["tokens"]),
            "-c", str(ctx), "-t", str(threads), "-b", str(batch), "--temp", str(temperature),
            "--no-display-prompt", "--perf",
        ]
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                input="/exit\n",
                text=True,
                capture_output=True,
                timeout=SAFE_SWEEP["timeout_seconds"],
            )
            returncode = completed.returncode
            output = (completed.stdout or "") + "\n" + (completed.stderr or "")
        except subprocess.TimeoutExpired as exc:
            returncode = 124
            output = (exc.stdout or "") + "\n" + (exc.stderr or "")
        elapsed_s = max(0.001, time.monotonic() - started)

    if returncode != 0:
        return {
            "status": classify_failure(output, returncode),
            "elapsed_seconds": round(elapsed_s, 3),
            "stderr_tail": output[-1200:],
        }

    prompt_tps, generation_tps = parse_raw_tps(output)
    generation_source = "raw"
    if generation_tps is None:
        generation_tps = f"{SAFE_SWEEP['tokens'] / elapsed_s:.2f}"
        generation_source = "estimated"
    return {
        "status": "OK",
        "elapsed_seconds": round(elapsed_s, 3),
        "prompt_tps": prompt_tps or "?",
        "generation_tps": generation_tps,
        "generation_source": generation_source,
        "output_tail": output[-1200:],
    }


def run_sweep(model_query: str) -> str:
    model = resolve_model(model_query)
    if model is None:
        return "Unknown model. Use `benchmark models` to list selectable model names."

    memory = load_memory()
    known = memory["known_models"].get(model.name, {})
    if known.get("status") == "corrupt":
        return f"{model.name} is recorded as CORRUPT. Replace the GGUF before tuning it."

    available, total = memory_mb()
    swap = swap_used_mb()
    if available < 550:
        return f"Benchmark deferred: only {available}MB RAM available ({swap}MB swap used). Free memory, then retry."

    configurations = [
        {"ctx": ctx, "threads": threads, "batch": batch, "temperature": SAFE_SWEEP["temperature"]}
        for ctx in SAFE_SWEEP["contexts"]
        for threads in SAFE_SWEEP["threads"]
        for batch in SAFE_SWEEP["batches"]
    ]
    run = {
        "id": f"sweep-{int(time.time())}",
        "timestamp": now_iso(),
        "model": model.name,
        "model_bytes": model.stat().st_size,
        "memory_before_mb": available,
        "swap_used_before_mb": swap,
        "prompt": DEFAULT_PROMPT,
        "configurations": [],
    }

    for index, config in enumerate(configurations, start=1):
        available, _ = memory_mb()
        if available < 500:
            entry = {**config, "status": "SKIPPED_LOW_MEMORY", "sequence": index}
        else:
            entry = {**config, "sequence": index, **run_configuration(model, **config)}
        run["configurations"].append(entry)
        if entry.get("status") == "CORRUPT":
            memory["known_models"][model.name] = {
                "status": "corrupt",
                "notes": "Detected by Lorna2 benchmark manager; llama.cpp reported model corruption.",
            }
            break

    successful = [
        row for row in run["configurations"]
        if row.get("status") == "OK" and row.get("generation_tps") not in (None, "?")
    ]
    if successful:
        best = max(successful, key=lambda row: float(row["generation_tps"]))
        run["best"] = best
        memory["recommendations"][model.name] = {
            "timestamp": now_iso(),
            "config": {key: best[key] for key in ("ctx", "threads", "batch", "temperature")},
            "generation_tps": best["generation_tps"],
            "generation_source": best.get("generation_source", "raw"),
            "status": "candidate",
        }
    else:
        run["best"] = None

    memory["runs"].append(run)
    memory["runs"] = memory["runs"][-20:]
    save_memory(memory)
    return format_run(run)


def format_run(run: dict[str, Any]) -> str:
    lines = [
        f"Lorna2 sweep: {run['model']}",
        f"Memory before: {run['memory_before_mb']}MB RAM available; {run['swap_used_before_mb']}MB swap used.",
        "ctx | threads | batch | temp | gen t/s | source | status",
    ]
    for row in run["configurations"]:
        lines.append(
            f"{row.get('ctx', '?'):>4} | {row.get('threads', '?'):>7} | {row.get('batch', '?'):>5} | "
            f"{row.get('temperature', '?'):>4} | {str(row.get('generation_tps', '?')):>7} | "
            f"{row.get('generation_source', '-'):>9} | {row.get('status', '?')}"
        )
    best = run.get("best")
    if best:
        source = "measured" if best.get("generation_source") == "raw" else "elapsed estimate"
        lines.append(
            f"Best candidate: ctx={best['ctx']} threads={best['threads']} batch={best['batch']} "
            f"temp={best['temperature']} at {best['generation_tps']} t/s ({source})."
        )
    else:
        lines.append("No usable configuration was recorded.")
    return "\n".join(lines)


def models_report() -> str:
    memory = load_memory()
    lines = ["Available model candidates:"]
    for path in discover_models():
        status = memory["known_models"].get(path.name, {}).get("status", "unclassified")
        lines.append(f"  {path.name} ({path.stat().st_size // (1024 * 1024)}MB) — {status}")
    return "\n".join(lines)


def memory_report() -> str:
    memory = load_memory()
    lines = ["Lorna2 benchmark memory:"]
    for model, recommendation in memory.get("recommendations", {}).items():
        config = recommendation.get("config", {})
        lines.append(
            f"  {model}: ctx={config.get('ctx')} threads={config.get('threads')} "
            f"batch={config.get('batch')} temp={config.get('temperature')} — "
            f"{recommendation.get('generation_tps')} t/s ({recommendation.get('generation_source')})"
        )
    if not memory.get("recommendations"):
        lines.append("  No completed sweep recommendations yet.")
    return "\n".join(lines)


def command(command_text: str) -> str:
    parts = command_text.strip().split(maxsplit=1)
    action = parts[0].lower() if parts else "help"
    argument = parts[1].strip() if len(parts) > 1 else ""
    if action in {"help", ""}:
        return (
            "Benchmark commands:\n"
            "  benchmark models              list local GGUF candidates\n"
            "  benchmark sweep qwen          run 8 safe Qwen configurations\n"
            "  benchmark sweep smollm        run 8 safe SmolLM configurations\n"
            "  benchmark memory              show retained benchmark recommendations\n"
            "  benchmark status              show RAM, swap, and runner availability"
        )
    if action == "models":
        return models_report()
    if action == "memory":
        return memory_report()
    if action == "status":
        available, total = memory_mb()
        binary = llama_binary() or "not found"
        return f"RAM available: {available}/{total}MB; swap used: {swap_used_mb()}MB; llama-cli: {binary}"
    if action == "sweep":
        return run_sweep(argument)
    return "Unknown benchmark action. Use `benchmark help`."


if __name__ == "__main__":
    print(command(" ".join(os.sys.argv[1:])))
