---
name: lorna-benchmark-orchestration
description: Run safe, sequential local GGUF configuration benchmarks on a resource-constrained Termux phone. Use when selecting a Lorna model, tuning context, threads, or batch size, recording results, or recommending the best speed-and-stability configuration.
---

# Lorna Benchmark Orchestration

Use this workflow to compare local models and runtime configurations without leaving hanging `llama-cli` processes or corrupting results.

## Operating Rules

1. Run **one model process at a time**. Never run parallel benchmarks on the 4 GB phone.
2. Begin with the core matrix: context `512, 1024`; generation threads `2, 4`; batch `32, 64`; temperature `0.2`. Only run runtime and sampling profiles after a core candidate exists.
3. Let the configured token limit complete before `/exit` is consumed. Do not send an exit command mid-response.
4. Apply a timeout per run. Record timeout, memory deferral, and model-load failures instead of retrying blindly.
5. Treat `corrupted or incomplete` and `not within the file bounds` as **CORRUPT**. Do not retest that GGUF until it is replaced.
6. Prefer raw llama.cpp prompt/generation timings. If the runner omits them, calculate generation throughput as `fixed generated tokens ÷ elapsed seconds` and label it **estimated**.
7. Save every completed configuration and the best speed candidate into durable benchmark memory before recommending a setting. Do not treat sampling speed alone as a quality recommendation.

## Lorna2 Commands

Use the benchmark command family in agent mode:

```text
benchmark status
benchmark models
benchmark profiles
benchmark sweep qwen core
benchmark sweep qwen runtime
benchmark sweep qwen sampling
benchmark sweep smollm core
benchmark apply qwen
benchmark optimize qwen
benchmark optimize all
benchmark active qwen
benchmark rollback qwen
benchmark memory
```

`benchmark sweep <model> core` runs the eight safe baseline combinations. `runtime` then varies context, generation threads, prompt/batch threads, logical and physical batch size, KV-cache precision, and flash-attention mode around the current best candidate. `sampling` varies temperature, top-k, top-p, min-p, and repeat penalty while retaining response tails for later quality review. Each completed configuration is retained in `agents/benchmark_memory.json`; reruns resume instead of repeating successful configurations.

## Application and Optimization

Use `benchmark apply <model>` only after a runtime candidate exists. The agent re-runs the candidate and activates it only when verification succeeds and reaches at least 70% of the recorded candidate throughput. Applied settings are device-local in `~/.lorna_v2/optimized_presets.json`, with the prior preset retained in history. Use `benchmark rollback <model>` to restore the previous setting or return to Lorna's automatic tier after the first application. Lorna's normal model runners load the active optimized preset automatically.

Use `benchmark optimize <model>` to resume the core, runtime, and sampling profiles then apply the verified winner. Use `benchmark optimize all` only when the device is idle and powered, because it sequentially optimizes every recorded safe candidate. Never apply a corrupt, low-memory-deferred, or unverified candidate.

## Recommendation Standard

Recommend only a configuration that completed all required tests without a crash or critical-memory deferral. Give the model name, context, thread count, batch size, temperature, speed, and whether the speed is raw or estimated. Explain when a faster small model should be used for responsiveness and when a slower larger model should be reserved for higher-quality reasoning.

## Current Device Knowledge

The phone is a Redmi 13C running Termux with roughly 3.7 GB usable RAM. Known safe candidates include Qwen 2.5 0.5B and SmolLM2 360M. TinyDolphin 2.8 1.1B is currently recorded as corrupt and must be skipped until its GGUF is replaced.

## Recovery

If a benchmark is interrupted, inspect durable benchmark memory first. Resume only missing configurations; do not overwrite completed results or launch another concurrent sweep.
