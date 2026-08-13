# Lorna2 Benchmark Agent

Lorna2 Agent can now coordinate safe local model configuration sweeps on the Termux phone. It keeps durable machine-readable state in `agents/benchmark_memory.json`, so a later agent session can inspect completed runs and recommendations instead of blindly repeating work.

## Start the agent

```bash
cd "$HOME/Lorna"
python3 agents/lorna_v2.py
```

Switch to agent mode when using ordinary tool commands:

```text
/node agent
```

The benchmark commands work directly as slash commands and can also be used without a slash in agent mode.

| Command | Purpose |
|---|---|
| `/benchmark status` | Show available RAM, swap use, and the `llama-cli` path. |
| `/benchmark models` | List local GGUF candidates and their remembered condition. |
| `/benchmark sweep qwen` | Run the eight safe configurations for Qwen 2.5 0.5B. |
| `/benchmark sweep smollm` | Run the eight safe configurations for SmolLM2 360M. |
| `/benchmark memory` | Show stored best candidates and their saved settings. |

The embedded training resource is dynamically available as:

```text
/skill use library:local/lorna-benchmark-orchestration/skill.md
```

## Safety and result rules

The sweep is sequential and uses context sizes `512` and `1024`, thread counts `2` and `4`, batch sizes `32` and `64`, and temperature `0.2`. Each run uses a fixed token budget, then supplies `/exit` after the response can complete. If raw llama.cpp timing lines are absent, Lorna2 uses a clearly labelled elapsed-time estimate.

Models marked **CORRUPT** are not retried. The current TinyDolphin GGUF is recorded as corrupt because llama.cpp reported tensor data outside the file bounds. The agent refuses new sweeps when memory is too constrained and persists every completed result before returning a recommendation.
