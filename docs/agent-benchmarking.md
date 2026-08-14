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
| `/benchmark profiles` | Show the staged core, runtime, and sampling profiles. |
| `/benchmark sweep qwen core` | Run the eight safe core configurations for Qwen 2.5 0.5B. |
| `/benchmark sweep qwen runtime` | Tune context, generation threads, prompt/batch threads, batch, ubatch, KV cache, and flash-attention mode around Qwen's best core configuration. |
| `/benchmark sweep qwen sampling` | Compare temperature, top-k, top-p, min-p, and repeat-penalty settings, retaining response excerpts for later quality review. |
| `/benchmark sweep smollm core` | Run the eight safe core configurations for SmolLM2 360M. |
| `/benchmark memory` | Show stored best candidates and their saved settings. |

The embedded training resource is dynamically available as:

```text
/skill use library:local/lorna-benchmark-orchestration/skill.md
```

## Safety and result rules

The **core** profile is sequential and uses context sizes `512` and `1024`, thread counts `2` and `4`, batch sizes `32` and `64`, and temperature `0.2`. The **runtime** profile tests one parameter family at a time around the retained best core setting: context, generation threads, prompt/batch threads, logical and physical batch sizes, KV-cache precision, and flash-attention mode. The **sampling** profile varies temperature, top-k, top-p, min-p, and repeat penalty. Each run uses a fixed token budget, then supplies `/exit` after the response can complete. If raw llama.cpp timing lines are absent, Lorna2 uses a clearly labelled elapsed-time estimate.

Completed configurations are keyed and retained, so profile reruns resume instead of repeating successful work. Models marked **CORRUPT** are not retried. The current TinyDolphin GGUF is recorded as corrupt because llama.cpp reported tensor data outside the file bounds. The agent refuses new sweeps when memory is too constrained and persists every completed result before returning a recommendation.
