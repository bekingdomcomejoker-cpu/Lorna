# LORNA v3 Enterprise Edition

**L**ocal **O**ffline **R**easoning **N**ode **A**rchitecture  
Production-grade LLM orchestration for 4GB Android devices

---

## What's New in v3

### 🔬 Parameter Tuning Lab
Systematic benchmark testing of all parameter combinations:
- Context: 512 → 8192
- Threads: 2 → 5  
- Batch: 16 → 256
- Temperature: 0.1 → 0.9

Automatically finds optimal config for each model. Based on real Redmi 13C benchmarks showing **DeepSeek R1: 5.0 t/s generation** @ 4GB RAM.

```bash
lorna tune quick    # 36 tests (~5 min)
lorna tune full     # 320 tests (~30 min)
lorna tune custom   # you define test matrix
```

### 💾 Persistent Memory
Session continuity across runs:
```bash
lorna chain 3 --save mysession
# Later...
lorna chain 3 --load mysession  # continues from where you left off
```

### ⚡ Preset System
Quick configs for common scenarios:
```bash
lorna solo --preset ultrafast   # ≤200MB models, max speed
lorna solo --preset deepseek_r1 # R1 optimal (5.0 t/s tested)
lorna solo --preset stable      # low RAM safety mode
```

Available presets:
- `ultrafast` — 512ctx/256batch/4t (≤200MB models)
- `speed` — 768ctx/128batch/4t (Qwen 0.5B daily driver)
- `balanced` — 1024ctx/64batch/4t (Llama 1B)
- `quality` — 2048ctx/48batch/3t (reasoning models)
- `deepseek_r1` — 4096ctx/32batch/3t (R1 @ 5.0t/s verified)
- `stable` — 512ctx/32batch/2t (extreme stability)

### 🎯 Per-Model Configs
Override defaults for specific models:
```bash
lorna config deepseek-r1 --ctx 4096 --threads 3 --batch 32 --temp 0.3
# Saved permanently for this model
```

### 📊 Analytics Dashboard
```bash
lorna stats              # performance summary
lorna stats --compare    # compare multiple tune runs
```

---

## Benchmark Results (Redmi 13C, 4GB RAM)

From actual testing (see DSBench.pdf data):

| Model | Context | Threads | Prompt t/s | Gen t/s | Notes |
|-------|---------|---------|-----------|---------|-------|
| DeepSeek R1 1.5B | 4096 | 3 | 11.7 | 5.0 | ⭐ Production verified |
| DeepSeek R1 1.5B | 8192 | 3 | 8.8 | 4.2 | Stable, slower |
| Llama 3.2 1B | 1024 | 4 | 14.5 | 6.8 | Daily driver |
| Qwen 0.5B | 768 | 4 | 21.0 | 15.0 | Speed champion |
| SmolLM 360M | 512 | 4 | 25.0 | 18.0 | Ultra-fast orchestrator |

**Key Finding:** `pthread_mutex_lock` errors only occur on force-kill (Ctrl+C). Clean `/exit` = no errors. System is stable.

---

## Install

```bash
git clone https://github.com/YOUR_USERNAME/lorna-mobile-llm ~/lorna-mobile-llm
cd ~/lorna-mobile-llm
bash install.sh
source ~/.bashrc
lorna
```

---

## All Commands

### Core Modes
```
lorna solo              # pick any model, interactive
lorna chain 2           # 2-model pipeline
lorna chain 3           # Reflex→Oracle→Warfare
lorna chain 10          # all top-10 sequential
lorna race 3            # 3 tiny models parallel
lorna cascade           # historical architecture
```

### v3 Enterprise Features
```
lorna tune quick        # parameter tuning lab (36 tests)
lorna tune full         # exhaustive sweep (320 tests)  
lorna config <model>    # set per-model overrides
lorna preset list       # show all presets
lorna stats             # analytics dashboard
lorna memory list       # saved sessions
```

### Tools
```
lorna bench             # benchmark all safe models
lorna health            # full diagnostics
lorna top10             # speed reference table
```

---

## Production Deployment Guide

### Step 1: Find Optimal Config
```bash
# Test your primary model
lorna tune quick

# Apply best config
lorna config your-model --apply-best
```

### Step 2: Set Up Presets for Team
```bash
# Edit ~/.lorna_presets
# Add custom presets for your use case
```

### Step 3: Enable Persistent Memory
```bash
# Add to your workflow scripts:
lorna chain 3 --save project_x
# Team members can load:
lorna chain 3 --load project_x
```

### Step 4: Monitor Performance
```bash
# Regular health checks
lorna health

# Track performance over time
lorna stats --history
```

---

## Architecture

```
lorna-mobile-llm/
├── lorna.sh              ← Main entry + router
├── install.sh
├── README_V3.md          ← This file
├── lib/
│   ├── core.sh           ← Binary detection, execution
│   ├── memory.sh         ← RAM management
│   ├── registry.sh       ← Model discovery
│   ├── presets.sh        ← NEW: Preset configs
│   └── persist.sh        ← NEW: Persistent memory
├── pipelines/
│   ├── solo.sh
│   ├── chain.sh
│   ├── race.sh
│   └── cascade.sh
├── tools/
│   ├── tune.sh           ← NEW: Parameter tuning lab
│   ├── bench.sh
│   └── health.sh
├── configs/              ← NEW: Per-model overrides
└── memory/               ← NEW: Saved sessions
```

---

## FAQ

**Q: Why does `pthread_mutex_lock` error appear?**  
A: Only happens on force-kill (Ctrl+C / swipe-close). Use `/exit` for clean shutdown. Not a stability issue.

**Q: Can I run 8192 context safely?**  
A: Depends on model size and RAM state. Use `lorna tune` to find your device's ceiling.

**Q: What's the fastest stable config?**  
A: For Redmi 13C: DeepSeek R1 @ 4096ctx/3t/32b = 5.0 t/s verified. See `lorna preset deepseek_r1`.

**Q: How do presets work with per-model configs?**  
A: Per-model configs override presets. Precedence: per-model > preset > tier default.

---

*Built from 100+ hours of real benchmarking on Redmi 13C. Every config is measured, not guessed.*
