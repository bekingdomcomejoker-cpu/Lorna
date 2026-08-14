# Lorna Runtime Integration

This document describes the first integration wave that consolidates reusable Android and Termux patterns into the canonical Lorna runtime. It keeps direct llama.cpp execution in Lorna and places routing, benchmark-aware policy, and multi-stage orchestration in Lorna2.

## Responsibilities

| Component | Responsibility |
|---|---|
| `tools/health.sh` | Existing interactive health report; now supports `--json` for structured read-only data. |
| `agents/runtime_integration.py` | Read-only status collection, routing-profile selection, and optional sequential Ollama pipelines. |
| `agents/model_registry.json` | Shared node models, vision pairings, and template modes. |
| `agents/routing_profiles.json` | Named routes and lightweight keyword-based automatic selection. |
| `agents/lorna_v2.py` | Exposes the new commands to the Lorna2 interactive agent. |

> **Execution rule:** Pipelines run one local model stage at a time. A stage artifact is written only after its response completes. No pipeline starts a vision model; vision remains explicit through the existing `/vision-bridge` and `/moondream-image` commands.

## Lorna Shell Health

The existing interactive report remains unchanged:

```bash
cd "$HOME/Lorna"
./lorna.sh health
```

For structured output suitable for another local tool:

```bash
./tools/health.sh --json
```

The JSON reports available RAM, swap use, free home storage, discovered GGUF files, local binary paths, and active local-model processes. It does not start or stop a model.

## Lorna2 Commands

```text
/system
/status
```

These commands render the same read-only local runtime state in a compact form.

```text
/route list
/route fast
/route auto "write a Python script to parse benchmark results"
```

`/route` describes the selected model route. It does not launch a model.

```text
/pipeline --dry-run balanced "Explain the latest benchmark result"
/pipeline code "Write a small Python parser for a benchmark log"
```

The dry run shows the exact sequential stages without launching a model. A real pipeline stores its stage files and `manifest.json` under:

```text
~/.lorna_v2/pipelines/<timestamp>/
```

## Current Profiles

| Profile | Stages | Intended use |
|---|---|---|
| `fast` | `fast` | Short, low-latency local response. |
| `balanced` | `fast → deep → fast` | Refine, reason, and present. |
| `code` | `fast → deep → code → fast` | Refine, plan, implement, and summarize. |
| `verify` | `fast → deep → fast` | Produce and review a local response. |
| `vision` | Explicit vision path only | Choose `/vision-bridge` or `/moondream-image`; no pipeline model starts. |

## Model Registry

The registry deliberately records both current and rollback-compatible vision pairs. The lightweight SmolVLM pair remains the preferred screenshot-analysis entry, while the modern 2025 Moondream2 pair is available for direct fixture-compatible image processing. The legacy 050824 pair remains recorded only as a rollback path.

When changing a model filename, projector, or chat-template mode, update `agents/model_registry.json` before touching each individual script. A future integration step will make all benchmark and vision modules read the registry directly.

## Validation

Run the local tests before publishing changes:

```bash
cd "$HOME/Lorna"
python3 -m py_compile agents/runtime_integration.py agents/lorna_v2.py
python3 agents/test_runtime_integration.py
bash -n tools/health.sh
```

On Termux, the following test is read-only and does not launch a model:

```bash
printf '/system\n/route auto "write a Python script"\n/pipeline --dry-run balanced "explain a benchmark result"\n/exit\n' | python3 agents/lorna_v2.py
```
