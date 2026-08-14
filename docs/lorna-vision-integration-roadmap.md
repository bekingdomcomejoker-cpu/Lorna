# Lorna Vision Benchmark and Lorna2 Integration Roadmap

**Purpose.** This roadmap assigns the current local-model, benchmark, and vision capabilities to the correct Lorna layers. It preserves the Redmi 13C rule that **only one local model process may run at a time**, while making measured settings reusable by both classic Lorna and Lorna2.

The guiding design is deliberately small-device-first: use the shell for direct, recoverable execution; use Lorna2 for structured orchestration, durable memory, and interpretation; and use the shared core only for settings that ordinary text-model runners can safely consume.

## Current baseline

The verified 2025 Moondream2 model pair and SmolVLM pair have different invocation requirements. Moondream2 uses its embedded template metadata, while SmolVLM requires its explicit `smolvlm` template. The paired benchmark therefore runs them **sequentially** with independent logs, rather than treating them as interchangeable text models.

| Capability | Current location | Status | Correct ownership |
|---|---|---:|---|
| Text GGUF runtime presets | `lib/core.sh` and `agents/benchmark_manager.py` | Implemented | **Shared core + Lorna2** |
| Text model benchmark sweeps and durable memory | `agents/benchmark_manager.py` | Implemented | **Lorna2** |
| Direct Moondream2 image command | `agents/moondream_image.py` | Implemented | **Lorna2 vision command** |
| SmolVLM image analysis | `agents/vision_to_code.py` / `agents/vision_bridge.py` | Implemented, mixed historical goals | **Lorna2 vision layer** |
| Sequential paired vision benchmark | `tools/benchmark_vision_models.sh` | Implemented | **Lorna tool, then Lorna2 adapter** |
| Main menu routing | `lorna.sh` | Existing entry points | **Classic Lorna shell** |
| Agent command dispatch | `agents/lorna_v2.py` | Existing command system | **Lorna2** |

## Benchmark interface added now

The reusable shell benchmark is located at:

```text
tools/benchmark_vision_models.sh
```

It is installed on the phone at:

```text
$HOME/bin/benchmark-vision-models
```

It keeps each model's known-safe baseline and can add **one variable at a time**. It does not build a combinatorial grid, which is important on the phone because each full vision image run is expensive.

| Control | llama.cpp setting | Why it belongs in the paired vision benchmark |
|---|---|---|
| `--threads 2,4` | `-t` and default `--threads-batch` | Measures decode and prompt-worker scaling together. |
| `--batch-threads 2,4` | `--threads-batch` | Isolates prompt/image batch processing from generation threads. |
| `--output-tokens 16,24` | `-n` | Bounds image-answer latency and prevents long, irrelevant continuations. |
| `--image-tokens 32,64` | `--image-max-tokens` | Measures the detail-versus-latency trade-off for compatible dynamic-resolution vision models. |

These parameters map directly to documented llama.cpp controls: `-t` configures generation threads, `--threads-batch` configures batch/prompt threads, `-n` caps generated tokens, and `--image-max-tokens` bounds dynamic-resolution image tokens. [1] The upstream benchmark tool likewise treats thread, batch, micro-batch, prompt, and generation parameters as independently sweepable test dimensions. [2]

## Target architecture

```text
Classic Lorna shell (lorna.sh)
├── menu and simple routes
├── text workflow commands
├── vision-bench → invokes the reusable shell benchmark
└── agent2 → launches Lorna2

Shared runtime layer (lib/core.sh)
├── text-model capability probing
├── active text-model preset loading
└── no vision-specific model/projector assumptions

Lorna2 orchestration (agents/)
├── benchmark_manager.py
│   ├── text sweeps and text presets
│   └── future vision benchmark registry and durable result reader
├── vision_benchmark.py              [new adapter]
│   ├── validated model-pair registry
│   ├── invokes tools/benchmark_vision_models.sh sequentially
│   ├── parses summary/logs into JSON
│   └── selects a recommendation only after a successful answer
├── moondream_image.py
│   └── direct image Q&A with an explicitly chosen pair/config
├── vision_bridge.py
│   └── SmolVLM analysis followed by a text-only second stage
└── lorna_v2.py
    ├── /vision-benchmark
    ├── /vision-results
    └── /vision-config
```

## Integration plan

### Phase 1 — Preserve the shell benchmark as the execution primitive

Keep `tools/benchmark_vision_models.sh` as the lowest-level, manual, diagnosable runner. It should remain usable when Python, Ollama, or Lorna2 are unavailable. It writes timestamped logs and a summary for every run. This is the appropriate Lorna-side command because the main shell should offer direct execution and simple recovery, not embed agent policy.

The next classic-shell route should be:

```text
lorna vision-bench [options]
```

It should invoke `tools/benchmark_vision_models.sh` and display the produced summary path. It must not automatically run on startup and must refuse to start while `ollama serve` is active.

### Phase 2 — Add a Lorna2 vision benchmark adapter

Create `agents/vision_benchmark.py`. Its responsibilities should be limited to structured orchestration:

1. maintain a registry of **matched** model/projector pairs and template requirements;
2. call the shell benchmark one configuration at a time;
3. parse elapsed time, exit status, `Prompt`/`Generation` timing where present, and captured response text;
4. store durable results in a new `vision_runs` section of `benchmark_memory.json`;
5. classify each result as `OK`, `TIMEOUT`, `UNSUPPORTED`, `NO_RESPONSE`, or `LOW_QUALITY`;
6. recommend a profile only when it finishes within its timeout and produces non-empty answer text.

The adapter must keep vision recommendations separate from text presets. A Moondream or SmolVLM projector configuration is not safe to apply through `lib/core.sh`'s text-only model runner.

### Phase 3 — Expose deliberate Lorna2 commands

Add these commands to `agents/lorna_v2.py` and its `/tools` help:

| Command | Responsibility |
|---|---|
| `/vision-benchmark [image] [profile]` | Run or resume a paired, sequential benchmark. |
| `/vision-results` | Display the latest structured per-model/per-configuration results. |
| `/vision-config <moondream2|smolvlm>` | Show the selected recommendation and the exact command arguments. |
| `/vision-run <model> <image> [question]` | Run one explicitly selected vision model with its stored recommendation. |

Do **not** overload `/benchmark apply`. It is currently designed for text presets and appropriately rejects paired vision models. The vision adapter needs its own explicit configuration command and own on-disk state.

### Phase 4 — Consolidate model-pair metadata

Move model-specific constants out of individual modules into a small registry, for example `agents/vision_models.json`:

```json
{
  "moondream2-2025": {
    "model": "moondream2-text-model-q4_k_m-vicuna-20250414.gguf",
    "mmproj": "moondream2-mmproj-f16-20250414.gguf",
    "template_mode": "embedded",
    "baseline": {"threads": 4, "threads_batch": 4, "n_predict": 24, "ctx": 1024, "batch": 32, "ubatch": 32, "image_max_tokens": 64}
  },
  "smolvlm-256m": {
    "model": "SmolVLM-256M-Instruct-Q4_K_M.gguf",
    "mmproj": "mmproj-SmolVLM-256M-Instruct-f16.gguf",
    "template_mode": "smolvlm-no-jinja",
    "baseline": {"threads": 4, "threads_batch": 4, "n_predict": 32, "ctx": 2048, "batch": 8, "ubatch": 8, "image_max_tokens": "auto"}
  }
}
```

Then `moondream_image.py`, `vision_bridge.py`, the shell benchmark, and the future Lorna2 adapter can consume the same pair definitions. This removes the current mismatch in which some vision paths still reference the older `050824` Moondream2 files.

### Phase 5 — Fix the screenshot-quality path before automatic routing

The fixture proves the 2025 Moondream2 pair can answer an image question, but the real tall screenshot still has unreliable post-encoding behavior. Treat this as a separate quality/reliability experiment, not as a default-routing decision.

Run an image-token sweep on the screenshot with the paired benchmark before changing defaults:

```bash
$HOME/bin/benchmark-vision-models \
  --threads 2,4 \
  --batch-threads 2,4 \
  --output-tokens 16,24 \
  --image-tokens 32,64 \
  /sdcard/DCIM/Screenshots/Screenshot_2026-08-13-21-01-26-055_com.inspiredandroid.kai.jpg \
  "Describe the visible screen in one short sentence."
```

After that, compare the image preparation paths rather than guessing: original image, current bounded JPEG, and a middle-resolution JPEG. Store both response relevance and elapsed time. Only promote a screenshot configuration if it succeeds twice in sequence.

### Phase 6 — Add regression coverage and documentation

Add tests for each model pair's command construction, explicit template policy, one-model-at-a-time enforcement, parser classification, resume behavior, and stale-response-file avoidance. Update the agent documentation with the direct benchmark and Lorna2 command surfaces.

## What to borrow from GitHub projects—and what not to copy

The design should borrow **patterns**, not large dependencies. llama.cpp's benchmark documentation supports independent sweeps and structured result formats; that maps well to Lorna's existing durable benchmark memory. [2] Droid AI Toolkit demonstrates Android-aware RAM checks, one-tool-at-a-time operation, and repairable Termux setup patterns; that maps well to Lorna's memory guards and user-facing shell commands. [3]

LLMRouter demonstrates how model selection can eventually be treated as a routing problem with structured candidates and measurable outcomes. [4] It is not a suitable direct dependency for this phone: its full routing stack is designed around training, API providers, and much heavier environments. Lorna should initially use a compact rule-based router built from its own measured hardware results.

| Adopt now | Defer |
|---|---|
| Explicit pair registry, measured result records, one-variable sweeps, durable JSON state, clear CLI commands | Learned router models, cloud evaluation pipelines, GPU-heavy training, external provider dependencies |
| Sequential model isolation and RAM guardrails | Concurrent VLM benchmarking or background model services on the 3.6 GiB phone |
| Exact-command display and per-run logs | Automatic changes to model defaults without successful verification |

## Recommended implementation order

1. Run the new shell sweep on the fixture with a small list of values.
2. Add the `vision_models.json` registry and update direct vision modules to consume it.
3. Create `vision_benchmark.py` to parse shell results into durable vision memory.
4. Add Lorna2 `/vision-benchmark`, `/vision-results`, and `/vision-config` commands.
5. Add `lorna vision-bench` as the classic-shell entry point.
6. Run screenshot-focused sweeps and promote only a repeatable result.

This order protects the working manual path, avoids an oversized rewrite, and keeps Lorna and Lorna2 responsibilities distinct.

## References

[1]: https://github.com/ggml-org/llama.cpp/blob/master/tools/cli/README.md "llama.cpp CLI parameter reference"
[2]: https://github.com/ggml-org/llama.cpp/blob/master/tools/llama-bench/README.md "llama.cpp benchmark tool"
[3]: https://github.com/niyazmft/droid-ai-toolkit "Droid AI Toolkit for Termux"
[4]: https://github.com/ulab-uiuc/LLMRouter "LLMRouter"
