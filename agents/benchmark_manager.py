#!/usr/bin/env python3
"""Durable, resource-aware benchmark orchestration for Lorna2 Agent."""

from __future__ import annotations

import hashlib
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
MEMORY_PATH = AGENT_DIR / "benchmark_memory.json"
PRESET_STATE_PATH = Path.home() / ".lorna_v2" / "optimized_presets.json"
MODELS_DIR = Path.home() / "models"
DEFAULT_PROMPT = "Explain the convergence of the p-series and relate it to the Riemann zeta function."
DEFAULT_CONFIG = {
    "ctx": 512,
    "threads": 4,
    "threads_batch": 4,
    "batch": 64,
    "ubatch": 64,
    "temperature": 0.2,
    "top_k": 40,
    "top_p": 0.95,
    "min_p": 0.05,
    "repeat_penalty": 1.05,
    "cache_k": "q4_0",
    "cache_v": "q4_0",
    "flash_attn": "auto",
}
PROFILE_TOKENS = {"core": 100, "runtime": 80, "sampling": 100}
PROFILE_TIMEOUT_SECONDS = {"core": 120, "runtime": 120, "sampling": 120}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_memory() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "device": {
            "label": "Redmi 13C / Helio G85 / Termux",
            "ram_mb": 3720,
            "notes": "Prefer sequential tests. Do not benchmark multiple models concurrently.",
        },
        "workflow_rules": [
            "Use only one llama-cli process at a time.",
            "Let the fixed token budget finish before queued /exit is consumed.",
            "Abort or skip a run when the model file is corrupt or memory is critically low.",
            "Use elapsed throughput only when llama.cpp does not emit raw timing lines; label it estimated.",
            "Run staged profiles separately and reuse completed configurations rather than repeating them.",
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
        "completed_configurations": {},
        "unsupported_parameters": {},
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
    memory["schema_version"] = max(2, int(memory.get("schema_version", 1)))
    return memory


def save_memory(memory: dict[str, Any]) -> None:
    temp = MEMORY_PATH.with_suffix(".json.tmp")
    temp.write_text(json.dumps(memory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(MEMORY_PATH)


def load_preset_state() -> dict[str, Any]:
    if not PRESET_STATE_PATH.exists():
        return {"schema_version": 1, "presets": {}, "history": []}
    try:
        state = json.loads(PRESET_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = {"schema_version": 1, "presets": {}, "history": []}
    state.setdefault("schema_version", 1)
    state.setdefault("presets", {})
    state.setdefault("history", [])
    return state


def save_preset_state(state: dict[str, Any]) -> None:
    PRESET_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = PRESET_STATE_PATH.with_suffix(".json.tmp")
    temp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(PRESET_STATE_PATH)


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
    return sorted(
        path for path in MODELS_DIR.glob("*.gguf")
        if path.stat().st_size > 50 * 1024 * 1024 and "mmproj" not in path.name.lower()
    )


def resolve_model(query: str) -> Path | None:
    raw_query = query.strip()
    query = raw_query.lower()
    models = discover_models()
    if not query:
        return None
    direct_path = Path(raw_query).expanduser()
    if direct_path.is_file() and direct_path.suffix.lower() == ".gguf":
        return direct_path
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


def llama_help() -> str:
    binary = llama_binary()
    if not binary:
        return ""
    try:
        completed = subprocess.run([binary, "--help"], capture_output=True, text=True, timeout=10)
        return (completed.stdout or "") + (completed.stderr or "")
    except (OSError, subprocess.SubprocessError):
        return ""


def supported_flag(help_text: str, flag: str) -> bool:
    return flag in help_text


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
    unsupported_markers = (
        "unknown argument", "unrecognized option", "not supported", "unsupported", "not compiled",
        "not available in this build", "flash attention is not supported",
    )
    if any(marker in lowered for marker in unsupported_markers):
        return "UNSUPPORTED"
    return f"ERROR({returncode})"


def baseline_config(memory: dict[str, Any], model_name: str) -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    recommendation = memory.get("recommendations", {}).get(model_name, {})
    config.update(recommendation.get("config", {}))
    config.setdefault("threads_batch", config.get("threads", 4))
    config.setdefault("ubatch", min(config.get("batch", 64), 64))
    return config


def profile_configurations(profile: str, base: dict[str, Any]) -> list[dict[str, Any]]:
    """Create a one-variable-at-a-time matrix around the current best candidate."""
    configs: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(label: str, **changes: Any) -> None:
        config = dict(base)
        config.update(changes)
        fingerprint = json.dumps(config, sort_keys=True)
        if fingerprint in seen:
            return
        seen.add(fingerprint)
        config["label"] = label
        configs.append(config)

    if profile == "core":
        for ctx in (512, 1024):
            for threads in (2, 4):
                for batch in (32, 64):
                    add(f"core ctx={ctx} t={threads} b={batch}", ctx=ctx, threads=threads,
                        threads_batch=threads, batch=batch, ubatch=min(batch, 64), temperature=0.2)
    elif profile == "runtime":
        add("baseline")
        for ctx in (256, 384, 768, 1024, 1536):
            add(f"ctx={ctx}", ctx=ctx)
        for threads in (1, 2, 3, 4):
            add(f"threads={threads}", threads=threads, threads_batch=threads)
        for threads_batch in (1, 2, 3, 4):
            add(f"threads_batch={threads_batch}", threads_batch=threads_batch)
        for batch, ubatch in ((16, 16), (32, 32), (64, 64), (96, 64), (128, 64)):
            add(f"batch={batch} ubatch={ubatch}", batch=batch, ubatch=ubatch)
        for cache_k, cache_v in (("q8_0", "q8_0"), ("f16", "f16")):
            add(f"cache_k={cache_k} cache_v={cache_v}", cache_k=cache_k, cache_v=cache_v)
        for flash_attn in ("off", "auto"):
            add(f"flash_attn={flash_attn}", flash_attn=flash_attn)
    elif profile == "sampling":
        add("sampling baseline")
        for temperature in (0.0, 0.1, 0.2, 0.4, 0.7):
            add(f"temperature={temperature}", temperature=temperature)
        for top_k in (20, 40, 80):
            add(f"top_k={top_k}", top_k=top_k)
        for top_p in (0.80, 0.90, 0.95):
            add(f"top_p={top_p}", top_p=top_p)
        for min_p in (0.0, 0.05, 0.10):
            add(f"min_p={min_p}", min_p=min_p)
        for repeat_penalty in (1.0, 1.05, 1.10):
            add(f"repeat_penalty={repeat_penalty}", repeat_penalty=repeat_penalty)
    else:
        raise ValueError(f"Unknown profile: {profile}")
    return configs


def configuration_key(model_name: str, profile: str, config: dict[str, Any]) -> str:
    canonical = {key: value for key, value in config.items() if key != "label"}
    digest = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()[:16]
    return f"{model_name}|{profile}|{digest}"


def unsupported_key(model_name: str, profile: str, config: dict[str, Any], base: dict[str, Any]) -> str:
    changed = {key: value for key, value in config.items() if key != "label" and base.get(key) != value}
    return f"{model_name}|{profile}|" + json.dumps(changed, sort_keys=True)


def config_summary(config: dict[str, Any]) -> str:
    return (
        f"ctx={config.get('ctx')} t={config.get('threads')}/{config.get('threads_batch')} "
        f"b={config.get('batch')}/{config.get('ubatch')} temp={config.get('temperature')} "
        f"k={config.get('top_k')} p={config.get('top_p')} min_p={config.get('min_p')} "
        f"rep={config.get('repeat_penalty')} cache={config.get('cache_k')}/{config.get('cache_v')} "
        f"fa={config.get('flash_attn')}"
    )


def build_command(binary: str, model: Path, prompt_file: Path, config: dict[str, Any], tokens: int, help_text: str) -> list[str]:
    command = [
        binary, "-m", str(model), "-f", str(prompt_file), "-n", str(tokens),
        "-c", str(config["ctx"]), "-t", str(config["threads"]),
        "-b", str(config["batch"]), "--temp", str(config["temperature"]),
        "--no-display-prompt", "--perf",
    ]
    if supported_flag(help_text, "--threads-batch"):
        command.extend(["--threads-batch", str(config["threads_batch"])])
    if supported_flag(help_text, "--ubatch-size"):
        command.extend(["--ubatch-size", str(config["ubatch"])])
    if supported_flag(help_text, "--top-k"):
        command.extend(["--top-k", str(config["top_k"])])
    if supported_flag(help_text, "--top-p"):
        command.extend(["--top-p", str(config["top_p"])])
    if supported_flag(help_text, "--min-p"):
        command.extend(["--min-p", str(config["min_p"])])
    if supported_flag(help_text, "--repeat-penalty"):
        command.extend(["--repeat-penalty", str(config["repeat_penalty"])])
    if supported_flag(help_text, "--cache-type-k"):
        command.extend(["--cache-type-k", str(config["cache_k"]), "--cache-type-v", str(config["cache_v"])])
    if supported_flag(help_text, "--flash-attn"):
        command.extend(["--flash-attn", str(config["flash_attn"])])
    return command


def run_configuration(model: Path, config: dict[str, Any], profile: str, help_text: str) -> dict[str, Any]:
    binary = llama_binary()
    if not binary:
        return {"status": "ERROR(no_llama_cli)"}
    tokens = PROFILE_TOKENS[profile]
    with tempfile.TemporaryDirectory(prefix="lorna2_benchmark_") as temp_dir:
        prompt_file = Path(temp_dir) / "prompt.txt"
        prompt_file.write_text(DEFAULT_PROMPT + "\n", encoding="utf-8")
        command = build_command(binary, model, prompt_file, config, tokens, help_text)
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                input="/exit\n",
                text=True,
                capture_output=True,
                timeout=PROFILE_TIMEOUT_SECONDS[profile],
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
    source = "raw"
    if generation_tps is None:
        generation_tps = f"{tokens / elapsed_s:.2f}"
        source = "estimated"
    return {
        "status": "OK",
        "elapsed_seconds": round(elapsed_s, 3),
        "prompt_tps": prompt_tps or "?",
        "generation_tps": generation_tps,
        "generation_source": source,
        "output_tail": output[-1200:],
    }


def run_sweep(model_query: str, profile: str = "core") -> str:
    model = resolve_model(model_query)
    if model is None:
        return "Unknown model. Use `benchmark models` to list selectable model names."
    if profile not in {"core", "runtime", "sampling"}:
        return "Profile must be core, runtime, or sampling."

    memory = load_memory()
    known = memory["known_models"].get(model.name, {})
    if known.get("status") == "corrupt":
        return f"{model.name} is recorded as CORRUPT. Replace the GGUF before tuning it."

    available, _ = memory_mb()
    swap = swap_used_mb()
    if available < 550:
        return f"Benchmark deferred: only {available}MB RAM available ({swap}MB swap used). Free memory, then retry."

    base = baseline_config(memory, model.name)
    configurations = profile_configurations(profile, base)
    help_text = llama_help()
    run = {
        "id": f"{profile}-{int(time.time())}",
        "timestamp": now_iso(),
        "profile": profile,
        "model": model.name,
        "model_bytes": model.stat().st_size,
        "memory_before_mb": available,
        "swap_used_before_mb": swap,
        "prompt": DEFAULT_PROMPT,
        "base_config": base,
        "configurations": [],
    }

    for index, config in enumerate(configurations, start=1):
        key = configuration_key(model.name, profile, config)
        blocked_key = unsupported_key(model.name, profile, config, base)
        prior = memory["completed_configurations"].get(key)
        if blocked_key in memory["unsupported_parameters"]:
            entry = {**config, "status": "SKIPPED_UNSUPPORTED", "sequence": index, "reused": True}
        elif prior and prior.get("status") in {"OK", "UNSUPPORTED"}:
            entry = {**config, **prior, "sequence": index, "reused": True}
        else:
            available, _ = memory_mb()
            if available < 500:
                entry = {**config, "status": "SKIPPED_LOW_MEMORY", "sequence": index}
            else:
                entry = {**config, "sequence": index, **run_configuration(model, config, profile, help_text)}
            memory["completed_configurations"][key] = {k: v for k, v in entry.items() if k != "sequence"}
            if entry.get("status") == "UNSUPPORTED":
                memory["unsupported_parameters"][blocked_key] = {
                    "timestamp": now_iso(),
                    "label": config.get("label", "runtime option"),
                    "reason": entry.get("stderr_tail", "")[-300:],
                }
        run["configurations"].append(entry)
        if entry.get("status") == "CORRUPT":
            memory["known_models"][model.name] = {
                "status": "corrupt",
                "notes": "Detected by Lorna2 benchmark manager; llama.cpp reported model corruption.",
            }
            break
        save_memory(memory)

    successful = [
        row for row in run["configurations"]
        if row.get("status") == "OK" and row.get("generation_tps") not in (None, "?")
    ]
    if successful:
        best = max(successful, key=lambda row: float(row["generation_tps"]))
        run["best"] = best
        if profile in {"core", "runtime"}:
            memory["recommendations"][model.name] = {
                "timestamp": now_iso(),
                "profile": profile,
                "config": {key: best[key] for key in DEFAULT_CONFIG},
                "generation_tps": best["generation_tps"],
                "generation_source": best.get("generation_source", "raw"),
                "status": "candidate",
            }
    else:
        run["best"] = None

    memory["runs"].append(run)
    memory["runs"] = memory["runs"][-30:]
    if len(memory["completed_configurations"]) > 250:
        keys = list(memory["completed_configurations"])[-250:]
        memory["completed_configurations"] = {key: memory["completed_configurations"][key] for key in keys}
    save_memory(memory)
    return format_run(run)


def format_run(run: dict[str, Any]) -> str:
    lines = [
        f"Lorna2 {run['profile']} sweep: {run['model']}",
        f"Memory before: {run['memory_before_mb']}MB RAM available; {run['swap_used_before_mb']}MB swap used.",
        "# | configuration | gen t/s | source | status",
    ]
    for row in run["configurations"]:
        reused = " reused" if row.get("reused") else ""
        lines.append(
            f"{row.get('sequence', '?'):>2} | {row.get('label', config_summary(row))} | "
            f"{str(row.get('generation_tps', '?')):>7} | {row.get('generation_source', '-'):>9} | "
            f"{row.get('status', '?')}{reused}"
        )
    best = run.get("best")
    if best:
        source = "measured" if best.get("generation_source") == "raw" else "elapsed estimate"
        lines.append(f"Best {run['profile']} candidate: {config_summary(best)} at {best['generation_tps']} t/s ({source}).")
    else:
        lines.append("No usable configuration was recorded.")
    return "\n".join(lines)


def apply_recommendation(model_query: str, verify: bool = True) -> str:
    model = resolve_model(model_query)
    if model is None:
        return "Unknown model. Use `benchmark models` to list selectable model names."
    memory = load_memory()
    recommendation = memory.get("recommendations", {}).get(model.name)
    if not recommendation:
        return f"No runtime recommendation exists for {model.name}. Run core and runtime profiles first."

    config = dict(DEFAULT_CONFIG)
    config.update(recommendation.get("config", {}))
    verification: dict[str, Any] | None = None
    if verify:
        available, _ = memory_mb()
        if available < 550:
            return f"Apply deferred: only {available}MB RAM available. Free memory and retry verification."
        verification = run_configuration(model, config, "runtime", llama_help())
        if verification.get("status") != "OK":
            return f"Apply cancelled: verification returned {verification.get('status')}. Existing preset was left unchanged."
        expected = float(recommendation.get("generation_tps", 0) or 0)
        observed = float(verification.get("generation_tps", 0) or 0)
        if expected > 0 and observed < expected * 0.70:
            return (
                f"Apply deferred: verification measured {observed:.2f} t/s, below the 70% stability floor of "
                f"{expected * 0.70:.2f} t/s. Existing preset was left unchanged."
            )

    state = load_preset_state()
    previous = state["presets"].get(model.name)
    preset = {
        "model": model.name,
        "model_path": str(model),
        "config": config,
        "source_profile": recommendation.get("profile", "runtime"),
        "source_speed_tps": recommendation.get("generation_tps"),
        "source_speed_kind": recommendation.get("generation_source"),
        "applied_at": now_iso(),
        "verification": verification,
    }
    state["presets"][model.name] = preset
    state["history"].append({"timestamp": now_iso(), "model": model.name, "previous": previous, "applied": preset})
    state["history"] = state["history"][-50:]
    save_preset_state(state)
    measured = verification.get("generation_tps") if verification else "not run"
    return f"Applied optimized preset for {model.name}: {config_summary(config)}. Verification: {measured} t/s."


def rollback_preset(model_query: str) -> str:
    model = resolve_model(model_query)
    if model is None:
        return "Unknown model. Use `benchmark models` to list selectable model names."
    state = load_preset_state()
    for entry in reversed(state.get("history", [])):
        if entry.get("model") != model.name:
            continue
        previous = entry.get("previous")
        if previous is None:
            state["presets"].pop(model.name, None)
            message = f"Removed the first applied optimized preset for {model.name}; Lorna will use its automatic tier."
        else:
            state["presets"][model.name] = previous
            message = f"Restored the previous optimized preset for {model.name}."
        state["history"].append({"timestamp": now_iso(), "model": model.name, "rollback": True, "restored": previous})
        state["history"] = state["history"][-50:]
        save_preset_state(state)
        return message
    return f"No preset history exists for {model.name}."


def optimize_model(model_query: str) -> str:
    model = resolve_model(model_query)
    if model is None:
        return "Unknown model. Use `benchmark models` to list selectable model names."
    memory = load_memory()
    if memory.get("known_models", {}).get(model.name, {}).get("status") == "corrupt":
        return f"{model.name} is recorded as CORRUPT. Replace the GGUF before optimization."

    outputs = []
    for profile in ("core", "runtime", "sampling"):
        outputs.append(run_sweep(model.name, profile))
    outputs.append(apply_recommendation(model.name, verify=True))
    return "\n\n".join(outputs)


def optimize_all() -> str:
    memory = load_memory()
    candidates = [
        name for name, details in memory.get("known_models", {}).items()
        if details.get("status") in {"safe_candidate", "candidate", "optimized"} and resolve_model(name)
    ]
    if not candidates:
        return "No safe model candidates are recorded. Run `benchmark models` and classify a candidate first."
    outputs = []
    for name in candidates:
        outputs.append(f"=== Optimizing {name} ===\n{optimize_model(name)}")
    return "\n\n".join(outputs)


def active_preset_line(model_query: str) -> str:
    model = resolve_model(model_query)
    if model is None:
        return ""
    preset = load_preset_state().get("presets", {}).get(model.name)
    if not preset:
        return ""
    config = dict(DEFAULT_CONFIG)
    config.update(preset.get("config", {}))
    values = (
        config["ctx"], config["batch"], config["threads"], config["temperature"],
        config["threads_batch"], config["ubatch"], config["cache_k"], config["cache_v"],
        config["flash_attn"], config["top_k"], config["top_p"], config["min_p"], config["repeat_penalty"],
    )
    return " ".join(str(value) for value in values)


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
        lines.append(
            f"  {model} [{recommendation.get('profile', 'core')}]: {config_summary(recommendation.get('config', {}))} — "
            f"{recommendation.get('generation_tps')} t/s ({recommendation.get('generation_source')})"
        )
    lines.append(f"  Retained completed configurations: {len(memory.get('completed_configurations', {}))}")
    lines.append(f"  Retained unsupported parameter sets: {len(memory.get('unsupported_parameters', {}))}")
    if not memory.get("recommendations"):
        lines.append("  No completed sweep recommendations yet.")
    return "\n".join(lines)


def profile_report() -> str:
    return (
        "Benchmark profiles:\n"
        "  core     8 baseline combinations: ctx, generation threads, batch.\n"
        "  runtime  runtime parameters around the current best: ctx, generation/batch threads, batch, ubatch, KV cache, flash attention.\n"
        "  sampling sampling parameters: temperature, top-k, top-p, min-p, repeat penalty.\n"
        "Profiles resume completed configurations from benchmark memory. Run one profile at a time."
    )


def command(command_text: str) -> str:
    parts = command_text.strip().split()
    action = parts[0].lower() if parts else "help"
    if action in {"help", ""}:
        return (
            "Benchmark commands:\n"
            "  benchmark status                         show RAM, swap, runner availability\n"
            "  benchmark models                         list local GGUF candidates\n"
            "  benchmark profiles                       describe staged parameter profiles\n"
            "  benchmark sweep qwen [core|runtime|sampling]\n"
            "  benchmark sweep smollm [core|runtime|sampling]\n"
            "  benchmark apply <qwen|smollm>            verify and activate the retained best preset\n"
            "  benchmark optimize <qwen|smollm|all>     run staged profiles then apply verified winners\n"
            "  benchmark active <qwen|smollm>           print the active optimized preset\n"
            "  benchmark rollback <qwen|smollm>         restore the previous preset or auto tier\n"
            "  benchmark memory                         show retained benchmark recommendations"
        )
    if action == "models":
        return models_report()
    if action == "profiles":
        return profile_report()
    if action == "memory":
        return memory_report()
    if action == "status":
        available, total = memory_mb()
        binary = llama_binary() or "not found"
        return f"RAM available: {available}/{total}MB; swap used: {swap_used_mb()}MB; llama-cli: {binary}"
    if action == "sweep":
        if len(parts) < 2:
            return "Usage: benchmark sweep <qwen|smollm> [core|runtime|sampling]"
        return run_sweep(parts[1], parts[2].lower() if len(parts) > 2 else "core")
    if action == "apply":
        if len(parts) != 2:
            return "Usage: benchmark apply <qwen|smollm>"
        return apply_recommendation(parts[1], verify=True)
    if action == "optimize":
        if len(parts) != 2:
            return "Usage: benchmark optimize <qwen|smollm|all>"
        return optimize_all() if parts[1].lower() == "all" else optimize_model(parts[1])
    if action == "active":
        if len(parts) != 2:
            return "Usage: benchmark active <qwen|smollm>"
        line = active_preset_line(parts[1])
        return line or "No active optimized preset is stored for that model."
    if action == "rollback":
        if len(parts) != 2:
            return "Usage: benchmark rollback <qwen|smollm>"
        return rollback_preset(parts[1])
    if action == "preset-line":
        if len(parts) != 2:
            return ""
        return active_preset_line(parts[1])
    return "Unknown benchmark action. Use `benchmark help`."


if __name__ == "__main__":
    print(command(" ".join(os.sys.argv[1:])))
