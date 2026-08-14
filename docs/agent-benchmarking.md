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
| `/benchmark sweep qwen sampling` | Compare advanced sampler settings, including granular top-k and repetition controls, retaining response excerpts for later quality review. |
| `/benchmark sweep smollm core` | Run the eight safe core configurations for SmolLM2 360M. |
| `/benchmark sweep smollm runtime` | Tune the retained SmolLM2 core candidate for context, threads, batches, cache precision, and flash-attention support. |
| `/benchmark sweep smollm sampling` | Benchmark SmolLM2’s advanced sampler controls, skipping only controls absent from its installed `llama-cli` build. |
| `/benchmark sweep moondream core` | Benchmark the paired Moondream2 vision GGUF at image-aware core settings. |
| `/benchmark sweep moondream runtime` | Tune Moondream2’s image-aware context, thread, batch, cache, and flash-attention settings. |
| `/benchmark sweep moondream sampling` | Compare supported sampler controls while keeping the same local image fixture and vision prompt. |
| `/benchmark apply qwen` | Re-run the retained winner for verification, then store it as Qwen's active device-local preset only if it remains within the stability floor. |
| `/benchmark optimize qwen` | Resume core, runtime, and sampling profiles, then verify and apply the resulting Qwen preset. |
| `/benchmark optimize all` | Progressively optimize every recorded safe candidate sequentially; completed configurations are reused. |
| `/benchmark active qwen` | Print the active optimized preset used by Lorna's normal runners. |
| `/benchmark rollback qwen` | Restore the previous preset, or return to Lorna's automatic tier when reversing the first application. |
| `/benchmark memory` | Show stored best candidates and their saved settings. |

The embedded training resource is dynamically available as:

```text
/skill use library:local/lorna-benchmark-orchestration/skill.md
```

## Safety and result rules

The **core** profile is sequential and uses context sizes `512` and `1024`, thread counts `2` and `4`, batch sizes `32` and `64`, and temperature `0.2`. The **runtime** profile tests one parameter family at a time around the retained best core setting: context, generation threads, prompt/batch threads, logical and physical batch sizes, KV-cache precision, and flash-attention mode.

The **sampling** profile remains one-variable-at-a-time, but now covers temperature; top-k values from `10` through `100`; top-p and min-p; repeat penalties from `1.00` through `1.20`; repetition windows; frequency and presence penalties; locally typical and tail-free sampling; dynamic temperature; DRY anti-repetition settings; and Mirostat modes `1` and `2` with targeted tau and eta combinations. It checks the local `llama-cli --help` output before execution. A row changing a sampler that the installed build does not advertise is stored as **SKIPPED_UNSUPPORTED**, rather than launched as a failing process. This allows older Termux builds and newer llama.cpp builds to use the same profile safely.

Each run uses a fixed token budget, then supplies `/exit` after the response can complete. If raw llama.cpp timing lines are absent, Lorna2 uses a clearly labelled elapsed-time estimate. Completed configurations are keyed and retained, so profile reruns resume instead of repeating successful work. The agent also records runtime parameter sets that the installed llama.cpp build reports as unsupported, then skips them in later runs instead of repeatedly failing. `apply` verifies the retained winner again and refuses to replace an active preset if measured throughput falls below 70% of the recorded candidate. Applied presets and rollback history are device-local under `~/.lorna_v2/optimized_presets.json`; normal Lorna model runners automatically consume an active preset for the corresponding GGUF, including any advanced sampler values supported by that local binary. Models marked **CORRUPT** are not retried. The current TinyDolphin GGUF is recorded as corrupt because llama.cpp reported tensor data outside the file bounds. The agent refuses new sweeps when memory is too constrained and persists every completed result before returning a recommendation.

## SmolLM2 optimization order

For the 360M SmolLM2 GGUF, run the profiles in order. This preserves the fast-model preference while preventing sampling results from being conflated with inefficient threads, batches, or context settings.

```bash
cd "$HOME/Lorna"
printf '/benchmark sweep smollm core\n/benchmark sweep smollm runtime\n/benchmark sweep smollm sampling\n/benchmark apply smollm\n/benchmark active smollm\n/exit\n' | python3 agents/lorna_v2.py
```

Use `benchmark optimize smollm` for the same staged workflow with automatic resume and verified application. Keep the phone idle and powered during the run because each profile is deliberately sequential.

## Moondream2 multimodal benchmark

The local `moondream2-050824-q5k.gguf` is a **vision model**. Lorna2 identifies it as a paired model, locates the colocated `moondream2-mmproj-050824-f16.gguf`, and uses the bundled deterministic image fixture with the prompt “Describe the image. Identify the blue rectangle, green circle, and red triangle.” The benchmark passes the model with `-m`, the projector with `--mmproj`, and the fixture through `--image`; these are the local-file multimodal inputs documented by llama.cpp. [1]

Moondream2 uses a conservative `2048`-context, `32`-batch, `0.1`-temperature baseline and its core sweep compares contexts `1024` and `2048`. Lorna2 refuses to start if the matching projector, image fixture, `--mmproj`, or `--image` support is absent. This avoids treating a multimodal model as an ordinary text GGUF. The historical Moondream2 llama.cpp example likewise supplies an image, a projector, a low temperature, and a `2048` context. [2]

Run Moondream2’s stages explicitly:

```bash
cd "$HOME/Lorna"
printf '/benchmark sweep moondream core\n/benchmark sweep moondream runtime\n/benchmark sweep moondream sampling\n/exit\n' | python3 agents/lorna_v2.py
```

Lorna2 retains the winning Moondream2 benchmark result, but does **not** apply it to normal Lorna text runners: those runners do not supply a projector or an image. Use the retained run for vision-model selection and implement a dedicated image request runner before activating Moondream2 for general Lorna requests.

## References

[1]: https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md "llama.cpp multimodal documentation"
[2]: https://huggingface.co/vikhyatk/moondream2/discussions/12 "Moondream2 GGUF discussion"
