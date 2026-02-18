# LORNA — Local Offline Reasoning Node Architecture  
**v2 — All bugs fixed**

> Run 1 → 10 LLMs locally on a 4GB Android phone, solo or chained.

**Target:** Redmi 13C · Helio G85 · 4GB RAM · Termux · llama.cpp · CPU-only

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

## Usage

```
lorna                   → interactive menu
lorna solo              → pick any model for interactive chat
lorna chain 2           → 2-model output chain
lorna chain 3           → 3-model chain (Reflex→Think→Code)
lorna chain 5           → 5-model chain
lorna chain 10          → all top-10 models sequentially
lorna race 3            → 3 tiny models simultaneously
lorna race 5            → 5 tiny models simultaneously
lorna cascade           → historical Reflex→Oracle→Warfare
lorna bench             → benchmark all safe models
lorna bench all         → benchmark every model on device
lorna bench top10       → benchmark top-10 only
lorna health            → full diagnostics
lorna top10             → speed reference table
```

---

## Top 10 Fastest Models (Redmi 13C, measured)

| # | Model | Gen t/s | Prompt t/s | MB |
|---|-------|---------|-----------|-----|
| 🥇 | Cerebras-111M | 39–46 | 84–89 | 75 |
| 🥈 | NeoX Tiny 125M | ~37 | ~118 | 105 |
| 🥉 | node1_rwkv7 | 28–29 | ~93 | 203 |
| 4 | Tool-270M | 22–23 | 89–99 | 274 |
| 5 | **SmolLM2-360M-Alt** ✅ | 18–22 | 52–83 | 369 |
| 6 | ERNIE-0.3B ✅ | 19–20 | 60–66 | 230 |
| 7 | **Qwen-Sentinel / Qwen2.5-0.5B** ✅ | 18–21 | 57–65 | 409 |
| 8 | SmolLM-360M ✅ | 13–15 | 22–25 | 259 |
| 9 | Qwen2.5-0.5B-Instruct ✅ | 14–15 | ~21 | 470 |
| 10 | **Llama-3.2-1B-Instruct** ✅ | 6.7 | 14–15 | 772 |

---

## Modes

### `solo` — Single Model Chat
Picks from all models found on device. RAM-safe: refuses to load if insufficient memory.

### `chain N` — N-Model Output Chain
```
Input → Model1(clean) → Model2(analyze) → ... → ModelN(present)
```
- Uses **Context Seizure**: each node's output is trimmed to 35 lines before passing forward  
- Auto-assigns roles: REFLEX → BENCHMARK → FAST → RELAY → ORGANIZER → ANALYST → SENTINEL → PROCESSOR → ORACLE → WARFARE  
- Skips nodes if RAM is critically low  

### `race N` — Parallel Model Battle
Models ≤300MB run **simultaneously**. Larger models degrade to sequential automatically.  
All outputs displayed side-by-side for comparison.

### `cascade` — Historical Architecture
The proven **Reflex → Oracle → Warfare** pattern from the TriLLM2 documents:
- **Reflex** (Qwen 0.5B): rewrites/cleans the input  
- **Oracle** (Gemma/R1): first-principles analysis in 3 steps  
- **Warfare** (DeepSeek Coder): executable Python code  

Model-specific prompt formats applied automatically:
- Gemma: `<start_of_turn>user ... <start_of_turn>model`  
- DeepSeek: `### Instruction: ... ### Response:`  
- Llama-3: `<|begin_of_text|><|start_header_id|>user<|end_header_id|>...`  
- Qwen: `<|im_start|>user ... <|im_end|>`  

### `bench` — Benchmark
Tests every model with a fixed prompt and reports real t/s. Sorted by generation speed.

### `health` — Diagnostics
Checks: binary collision, RAM state, model inventory, top-10 resolution, PATH duplicates, zombie processes, binary smoke test.

---

## What Was Fixed in v2

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| Menu invisible in solo | `$(build_model_menu)` captured all output | Display output to `stderr`, only count to `stdout` |
| llama-cli hangs after output | No stdin close → waits for more input | Added `< /dev/null` for models ≤1000MB |
| `-t ""` crash (empty threads) | `"768 96  4 0.6"` double-space → `read` skipped field | Single-space strings in all tier config |
| Models not found in chain/race | Exact filename match only | Added fuzzy keyword match + size-sorted fallback |
| bench t/s always `?` | Wrong grep pattern for actual llama.cpp output format | Match `"N.NN tokens per second"` pattern |
| Race parallel=true on large models | Mixed list with wrong flag | Separate parallel/sequential lists, process independently |
| `pgrep -a` crash on some Termux builds | Flag not available | `ps aux \| grep` fallback |
| cascade fails if exact filenames missing | Hard-coded find patterns | Smart `find_best_model()` with role-aware fallback |
| Menu output lost after pipeline runs | `clear` in `show_menu` too early | Press-Enter gate before redraw |
| Silent kill of other sessions in solo | `cleanup_llama()` called unconditionally | Ask first if another llama-cli is running |

---

## Optimal Config Per Model Size

| Size | ctx | batch | threads | Behaviour |
|------|-----|-------|---------|-----------|
| ≤150MB | 512 | 256 | 4 | ultra-fast race models |
| 150–350MB | 768 | 128 | 4 | tiny models |
| 350–800MB | 768 | 96 | 4 | small daily drivers |
| 800MB–1.2GB | 1024 | 64 | 4 | medium models |
| 1.2–1.8GB | 768 | 48 | 3 | heavy models |
| >1.8GB | 512 | 32 | 2 | extreme — use with care |

KV cache: always `q4_0` (reduces RAM pressure vs f16, stable across all tested models)

---

## RAM Safety Reference

| Free RAM | Swap Used | Recommendation |
|----------|-----------|----------------|
| >1000MB | <1000MB | Run any model |
| 600–1000MB | <1400MB | ≤1B models |
| 400–600MB | any | ≤500MB models only |
| <400MB | any | **Restart Termux first** |

---

## Project Structure

```
lorna-mobile-llm/
├── lorna.sh              ← Entry point + router
├── install.sh            ← Setup: permissions, PATH, llama.cpp build
├── README.md
├── lib/
│   ├── core.sh           ← Binary detection, tier config, run_model, run_model_interactive
│   ├── memory.sh         ← RAM awareness, OOM prevention, cleanup
│   └── registry.sh       ← Top-10 registry, fuzzy model scan, menu builder
├── pipelines/
│   ├── solo.sh           ← Single model interactive
│   ├── chain.sh          ← N-model output chain (1–10)
│   ├── race.sh           ← Parallel tiny model race
│   └── cascade.sh        ← Reflex → Oracle → Warfare
├── tools/
│   ├── bench.sh          ← Benchmark with real t/s parsing
│   └── health.sh         ← Full system diagnostics
└── logs/                 ← Session logs (auto-created)
```

---

## Troubleshooting

**"No models found"** → Run `lorna health`. Models must be real GGUF files >50MB.  
**">>> hangs"** → Wrong binary (4.5MB build). `lorna health` detects this automatically.  
**Termux closes mid-pipeline** → OOM. Check RAM: `free -m`. Reduce chain size or restart Termux.  
**QQQQQ spam** → Missing chat template. LORNA v2 auto-detects model family and applies correct format.

---

*Built from real measurements on device. No guesswork.*
