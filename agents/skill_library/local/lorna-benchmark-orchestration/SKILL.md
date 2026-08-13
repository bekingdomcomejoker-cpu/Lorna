---
name: lorna-benchmark-orchestration
description: Run safe, sequential local GGUF configuration benchmarks on a resource-constrained Termux phone. Use when selecting a Lorna model, tuning context, threads, or batch size, recording results, or recommending the best speed-and-stability configuration.
---

# Lorna Benchmark Orchestration

Use this workflow to compare local models and runtime configurations without leaving hanging `llama-cli` processes or corrupting results.

## Operating Rules

1. Run **one model process at a time**. Never run parallel benchmarks on the 4 GB phone.
2. Begin with a small safe matrix: context `512, 1024`; threads `2, 4`; batch `32, 64`; temperature `0.2`.
3. Let the configured token limit complete before `/exit` is consumed. Do not send an exit command mid-response.
4. Apply a timeout per run. Record timeout, memory deferral, and model-load failures instead of retrying blindly.
5. Treat `corrupted or incomplete` and `not within the file bounds` as **CORRUPT**. Do not retest that GGUF until it is replaced.
6. Prefer raw llama.cpp prompt/generation timings. If the runner omits them, calculate generation throughput as `fixed generated tokens ÷ elapsed seconds` and label it **estimated**.
7. Save every completed run and the best candidate into durable benchmark memory before recommending a setting.

## Lorna2 Commands

Use the benchmark command family in agent mode:

```text
benchmark status
benchmark models
benchmark sweep qwen
benchmark sweep smollm
benchmark memory
```

`benchmark sweep <model>` runs the eight safe configurations and stores the complete result plus the best candidate in `agents/benchmark_memory.json`.

## Recommendation Standard

Recommend only a configuration that completed all required tests without a crash or critical-memory deferral. Give the model name, context, thread count, batch size, temperature, speed, and whether the speed is raw or estimated. Explain when a faster small model should be used for responsiveness and when a slower larger model should be reserved for higher-quality reasoning.

## Current Device Knowledge

The phone is a Redmi 13C running Termux with roughly 3.7 GB usable RAM. Known safe candidates include Qwen 2.5 0.5B and SmolLM2 360M. TinyDolphin 2.8 1.1B is currently recorded as corrupt and must be skipped until its GGUF is replaced.

## Recovery

If a benchmark is interrupted, inspect durable benchmark memory first. Resume only missing configurations; do not overwrite completed results or launch another concurrent sweep.
