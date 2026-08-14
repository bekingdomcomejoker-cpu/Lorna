#!/usr/bin/env python3
"""Shared runtime integration for Lorna2.

The module keeps model selection data in JSON, reports phone health without
launching inference, and coordinates optional sequential Ollama pipelines.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

AGENT_DIR = Path(__file__).resolve().parent
REGISTRY_PATH = AGENT_DIR / "model_registry.json"
PROFILES_PATH = AGENT_DIR / "routing_profiles.json"
ARTIFACT_ROOT = Path.home() / ".lorna_v2" / "pipelines"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not load {path.name}: {exc}") from exc


def model_registry() -> dict[str, Any]:
    return _load_json(REGISTRY_PATH)


def routing_profiles() -> dict[str, Any]:
    return _load_json(PROFILES_PATH)


def _meminfo() -> dict[str, int]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, value, *_ = line.split()
            values[key.rstrip(":")] = int(value) // 1024
    except (OSError, ValueError):
        pass
    return values


def _running_local_models() -> list[str]:
    try:
        result = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=5, check=False
        )
        return [
            line for line in result.stdout.splitlines()
            if any(token in line for token in ("llama-cli", "llama-mtmd-cli", "ollama serve"))
            and "runtime_integration" not in line
        ]
    except (OSError, subprocess.SubprocessError):
        return []


def system_status() -> dict[str, Any]:
    """Return a compact, read-only status record for the local phone runtime."""
    mem = _meminfo()
    models_dir = Path.home() / "models"
    model_files = []
    if models_dir.is_dir():
        for path in sorted(models_dir.glob("*.gguf")):
            try:
                model_files.append({"name": path.name, "size_mb": path.stat().st_size // (1024 * 1024)})
            except OSError:
                continue
    disk = shutil.disk_usage(str(Path.home()))
    available_ram = mem.get("MemAvailable", 0)
    swap_total = mem.get("SwapTotal", 0)
    swap_free = mem.get("SwapFree", 0)
    return {
        "schema_version": 1,
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "memory": {
            "total_mb": mem.get("MemTotal", 0),
            "available_mb": available_ram,
            "swap_used_mb": max(0, swap_total - swap_free),
            "admission": (
                "healthy" if available_ram >= 1000 else "moderate" if available_ram >= 600
                else "tight" if available_ram >= 400 else "critical"
            ),
        },
        "storage": {"home_free_mb": disk.free // (1024 * 1024)},
        "binaries": {
            "llama_cli": shutil.which("llama-cli"),
            "llama_mtmd_cli": shutil.which("llama-mtmd-cli"),
            "ollama": shutil.which("ollama"),
        },
        "models": model_files,
        "active_processes": _running_local_models(),
    }


def format_system_status() -> str:
    status = system_status()
    memory = status["memory"]
    binaries = status["binaries"]
    lines = [
        "Lorna runtime status:",
        f"  RAM available: {memory['available_mb']}/{memory['total_mb']}MB; swap used: {memory['swap_used_mb']}MB; admission: {memory['admission']}",
        f"  Home storage free: {status['storage']['home_free_mb']}MB",
        f"  llama-cli: {binaries['llama_cli'] or 'not found'}",
        f"  llama-mtmd-cli: {binaries['llama_mtmd_cli'] or 'not found'}",
        f"  ollama: {binaries['ollama'] or 'not found'}",
        f"  GGUF files in ~/models: {len(status['models'])}",
    ]
    if status["active_processes"]:
        lines.append("  Active local-model processes:")
        lines.extend(f"    {line}" for line in status["active_processes"])
    else:
        lines.append("  Active local-model processes: none")
    return "\n".join(lines)


def _profile_for_request(request: str, profiles: dict[str, Any]) -> str:
    lowered = request.lower()
    for profile_name in ("code", "verify", "vision", "balanced"):
        for keyword in profiles.get("classification_rules", {}).get(profile_name, []):
            if re.search(rf"\b{re.escape(keyword.lower())}\b", lowered):
                return profile_name
    return "fast"


def _describe_profile(name: str, profile: dict[str, Any], registry: dict[str, Any]) -> str:
    if "vision_path" in profile:
        vision = registry.get("vision", {}).get(profile["vision_path"], {})
        return (
            f"Profile '{name}': {profile.get('description', '')}\n"
            f"  vision path: {profile['vision_path']} ({vision.get('model_filename', 'unregistered')})"
        )
    stages = profile.get("stages", [])
    details = []
    for stage in stages:
        node = registry.get("nodes", {}).get(stage, {})
        details.append(f"{stage}={node.get('model', 'unregistered')}")
    return f"Profile '{name}': {profile.get('description', '')}\n  stages: {' -> '.join(details)}"


def route_command(argument: str) -> str:
    registry = model_registry()
    profiles = routing_profiles().get("profiles", {})
    argument = argument.strip()
    if not argument or argument == "list":
        lines = ["Lorna2 routing profiles:"]
        lines.extend(f"  {name:<10} {profile.get('description', '')}" for name, profile in profiles.items())
        lines.append("Use /route <profile> or /route auto <request>.")
        return "\n".join(lines)
    if argument.startswith("auto "):
        request = argument[5:].strip()
        if not request:
            return "Usage: /route auto <request>"
        name = _profile_for_request(request, routing_profiles())
        return f"Auto-selected {name}.\n{_describe_profile(name, profiles[name], registry)}"
    profile = profiles.get(argument)
    if profile is None:
        return f"Unknown route profile: {argument}. Use /route list."
    return _describe_profile(argument, profile, registry)


def _stage_prompt(stage: str, original_request: str, previous: str) -> str:
    context = previous.strip() or "(no previous stage output)"
    if stage == "fast":
        return (
            "Respond concisely and accurately using the current task and any prior stage output. "
            f"Task: {original_request}\nPrior output: {context}"
        )
    if stage == "deep":
        return (
            "Develop a practical step-by-step plan. Keep it grounded in the stated task and prior output. "
            f"Task: {original_request}\nPrior output: {context}"
        )
    if stage == "code":
        return (
            "Produce the requested implementation or technical answer. Prefer complete, usable output. "
            f"Task: {original_request}\nPrior output: {context}"
        )
    return f"Task: {original_request}\nPrior output: {context}"


def pipeline_preview(profile_name: str, request: str) -> str:
    registry = model_registry()
    profiles = routing_profiles().get("profiles", {})
    profile = profiles.get(profile_name)
    if profile is None:
        return f"Unknown pipeline profile: {profile_name}. Use /route list."
    if "vision_path" in profile:
        return (
            f"Pipeline preview for '{profile_name}': vision requests are handled by /vision-bridge or "
            f"/moondream-image; no text pipeline will launch."
        )
    lines = [f"Pipeline preview: {profile_name}", f"  request: {request}", "  execution: sequential only"]
    for index, stage in enumerate(profile.get("stages", []), start=1):
        model = registry.get("nodes", {}).get(stage, {}).get("model", "unregistered")
        lines.append(f"  {index}. {stage}: {model}")
    return "\n".join(lines)


def run_pipeline(
    profile_name: str,
    request: str,
    *,
    chat: Callable[[str, str], str] | None = None,
) -> str:
    """Run an opt-in, sequential local pipeline and keep stage artifacts."""
    registry = model_registry()
    profiles = routing_profiles().get("profiles", {})
    profile = profiles.get(profile_name)
    if profile is None:
        return f"Unknown pipeline profile: {profile_name}. Use /route list."
    if "vision_path" in profile:
        return "Vision profile selected. Use /vision-bridge or /moondream-image; no text model was launched."
    stages = profile.get("stages", [])
    if not stages:
        return f"Profile '{profile_name}' has no runnable stages."

    if chat is None:
        try:
            import ollama
        except ImportError:
            return "The ollama Python package is required for /pipeline."

        def chat(model: str, prompt: str) -> str:
            response = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
            return response["message"]["content"]

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    artifact_dir = ARTIFACT_ROOT / stamp
    artifact_dir.mkdir(parents=True, exist_ok=True)
    previous = ""
    outputs: list[tuple[str, str, Path]] = []
    try:
        for index, stage in enumerate(stages, start=1):
            node = registry.get("nodes", {}).get(stage)
            if not node:
                return f"Pipeline registry is missing node '{stage}'. No later stage was launched."
            prompt = _stage_prompt(stage, request, previous)
            output = chat(node["model"], prompt)
            output_path = artifact_dir / f"{index:02d}_{stage}.md"
            output_path.write_text(output.rstrip() + "\n", encoding="utf-8")
            outputs.append((stage, output, output_path))
            previous = output
    except Exception as exc:
        return f"Pipeline stopped at {stage}: {exc}\nArtifacts kept in: {artifact_dir}"

    manifest = {
        "profile": profile_name,
        "request": request,
        "stages": [{"node": stage, "path": str(path)} for stage, _output, path in outputs],
    }
    (artifact_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    lines = [f"Pipeline completed: {profile_name}", f"Artifacts: {artifact_dir}"]
    lines.extend(f"  {stage}: {path.name}" for stage, _output, path in outputs)
    lines.append("Final response:")
    lines.append(previous)
    return "\n".join(lines)


def pipeline_command(argument: str) -> str:
    try:
        tokens = shlex.split(argument)
    except ValueError as exc:
        return f"Invalid pipeline arguments: {exc}"
    if not tokens:
        return "Usage: /pipeline [--dry-run] <fast|balanced|code|verify|vision> <request>"
    dry_run = tokens[0] == "--dry-run"
    if dry_run:
        tokens = tokens[1:]
    if len(tokens) < 2:
        return "Usage: /pipeline [--dry-run] <profile> <request>"
    profile_name = tokens[0]
    request = " ".join(tokens[1:]).strip()
    if dry_run:
        return pipeline_preview(profile_name, request)
    return run_pipeline(profile_name, request)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Lorna2 runtime integration helpers")
    parser.add_argument("--system-json", action="store_true", help="print read-only runtime status as JSON")
    parser.add_argument("--route", metavar="ARGUMENT", help="run the routing-profile command")
    parser.add_argument("--pipeline", metavar="ARGUMENT", help="run or preview a sequential pipeline")
    options = parser.parse_args()
    if options.system_json:
        print(json.dumps(system_status(), indent=2, sort_keys=True))
    elif options.route is not None:
        print(route_command(options.route))
    elif options.pipeline is not None:
        print(pipeline_command(options.pipeline))
    else:
        parser.print_help()
