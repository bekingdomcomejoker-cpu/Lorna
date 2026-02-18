#!/bin/bash
# ============================================================
# LORNA — tools/bench.sh  (v2 — all bugs fixed)
# Benchmark all models and produce ranked leaderboard.
#
# BUG FIXED: t/s parsing now matches actual llama.cpp stderr format.
# llama.cpp outputs lines like:
#   "prompt eval time = 1234.56 ms / 8 tokens (154.32 ms per token, 6.48 tokens per second)"
#   "eval time       = 5678.90 ms / 32 runs  ( 177.47 ms per token,  5.63 tokens per second)"
# ============================================================

LORNA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$LORNA_DIR/lib/core.sh"
source "$LORNA_DIR/lib/memory.sh"
source "$LORNA_DIR/lib/registry.sh"

TMP_DIR="$LORNA_TMP/bench"
RESULTS_FILE="$HOME/lorna_bench_results.txt"
BENCH_PROMPT="Explain in one short paragraph what RAM is."
BENCH_TOKENS=32

mkdir -p "$TMP_DIR"

# ─── PARSE t/s FROM llama.cpp STDERR ────────────────────────
# BUG FIXED: Correct patterns for actual llama.cpp output format.
# Captures the final number before "tokens per second" on each line.
parse_tps_from_stderr() {
  local stderr_file="$1"
  local prompt_tps="" gen_tps=""

  # Match lines containing "prompt eval time" and extract last float
  local prompt_line
  prompt_line=$(grep "prompt eval time" "$stderr_file" 2>/dev/null | tail -1)
  if [[ -n "$prompt_line" ]]; then
    prompt_tps=$(echo "$prompt_line" | grep -oE '[0-9]+\.[0-9]+[[:space:]]+tokens per second' \
      | grep -oE '^[0-9]+\.[0-9]+' | tail -1)
  fi

  # Match "eval time" lines (NOT prompt eval) — that's generation
  local gen_line
  gen_line=$(grep "eval time" "$stderr_file" 2>/dev/null | grep -v "prompt" | tail -1)
  if [[ -n "$gen_line" ]]; then
    gen_tps=$(echo "$gen_line" | grep -oE '[0-9]+\.[0-9]+[[:space:]]+tokens per second' \
      | grep -oE '^[0-9]+\.[0-9]+' | tail -1)
  fi

  # Fallback: any "t/s" style output (newer llama.cpp versions)
  if [[ -z "$prompt_tps" ]]; then
    prompt_tps=$(grep -E "prompt.*[0-9]+\.[0-9]+ t/s" "$stderr_file" 2>/dev/null \
      | grep -oE '[0-9]+\.[0-9]+ t/s' | grep -oE '^[0-9]+\.[0-9]+' | tail -1)
  fi
  if [[ -z "$gen_tps" ]]; then
    gen_tps=$(grep -E "(eval|generate).*[0-9]+\.[0-9]+ t/s" "$stderr_file" 2>/dev/null \
      | grep -v "prompt" | grep -oE '[0-9]+\.[0-9]+ t/s' | grep -oE '^[0-9]+\.[0-9]+' | tail -1)
  fi

  echo "${prompt_tps:-?}|${gen_tps:-?}"
}

# ─── BENCHMARK ONE MODEL ────────────────────────────────────
bench_model() {
  local model="$1"
  local name size_mb
  name=$(basename "$model" .gguf)
  size_mb=$(du -m "$model" | cut -f1)
  local class
  class=$(model_load_class "$model")

  if [[ "$class" == "UNSAFE" ]]; then
    echo "${name}|${size_mb}|?|?|SKIPPED"
    return 0
  fi

  echo "$BENCH_PROMPT" > "$TMP_DIR/bench_prompt.txt"

  local start_ms end_ms
  start_ms=$(date +%s%3N)

  "$LLAMA_BIN" \
    -m  "$model"                  \
    -f  "$TMP_DIR/bench_prompt.txt" \
    -n  "$BENCH_TOKENS"           \
    --temp 0.1                    \
    --no-display-prompt           \
    2>"$TMP_DIR/bench_stderr.txt" > "$TMP_DIR/bench_stdout.txt" < /dev/null

  end_ms=$(date +%s%3N)
  local elapsed_ms=$(( end_ms - start_ms ))

  local tps_result
  tps_result=$(parse_tps_from_stderr "$TMP_DIR/bench_stderr.txt")
  local prompt_tps="${tps_result%%|*}"
  local gen_tps="${tps_result##*|}"

  local result_line="${name}|${size_mb}|${prompt_tps}|${gen_tps}|${elapsed_ms}ms|${class}"
  echo "$result_line"
  echo "$result_line" >> "$RESULTS_FILE"

  sleep 1; sync 2>/dev/null
}

# ─── DISPLAY SORTED RESULTS TABLE ───────────────────────────
show_results_table() {
  echo ""
  echo -e "${CYAN}${BOLD}  ═══════════════════════════════════════════════════════════${NC}"
  echo -e "${CYAN}${BOLD}  BENCHMARK RESULTS — sorted by generation speed${NC}"
  echo -e "${CYAN}${BOLD}  ═══════════════════════════════════════════════════════════${NC}"
  printf "  ${GOLD}%-38s %6s  %8s  %8s  %s${NC}\n" "MODEL" "MB" "PROMPT" "GEN" "STATUS"
  echo -e "  ${DIM}──────────────────────────────────────────────────────────${NC}"

  # BUG FIXED: Sort on gen_tps field (4th pipe-delimited field) numerically
  # Previous version used -k4 on space-delimited which broke with '?' values
  grep -v "^==\|^Device\|^Bench\|^$" "$RESULTS_FILE" 2>/dev/null \
    | sort -t'|' -k4 -rn 2>/dev/null \
    | while IFS='|' read -r name mb prompt gen elapsed class; do
        printf "  %-38s %6s  %8s  %8s  %s\n" \
          "${name:0:38}" "$mb" "${prompt}t/s" "${gen}t/s" "$class"
      done

  echo ""
  ok "Full results saved: $RESULTS_FILE"
}

# ─── MAIN ───────────────────────────────────────────────────
run_bench() {
  local mode="${1:-safe}"

  lorna_banner
  echo -e "  ${BOLD}MODE: BENCHMARK — ${mode}${NC}"
  echo ""
  print_ram_status
  echo ""

  {
    echo "=== LORNA Benchmark === $(date)"
    echo "Device: Redmi 13C | Binary: $(basename "$LLAMA_BIN") | Mode: $mode"
    echo ""
  } > "$RESULTS_FILE"

  local models=()

  case "$mode" in
    top10)
      while IFS= read -r path; do
        models+=("$path")
      done < <(get_top_n_paths 10)
      ;;
    safe)
      while IFS= read -r path; do
        local mb
        mb=$(du -m "$path" 2>/dev/null | cut -f1)
        (( mb <= 1200 )) && models+=("$path")
      done < <(scan_all_models)
      ;;
    all)
      while IFS= read -r path; do
        models+=("$path")
      done < <(scan_all_models)
      ;;
    *)
      err "Unknown mode: $mode  (use: all | safe | top10)"
      return 1
      ;;
  esac

  if (( ${#models[@]} == 0 )); then
    err "No models found."
    return 1
  fi

  info "Benchmarking ${#models[@]} models"
  info "Prompt: \"$BENCH_PROMPT\""
  info "Tokens per test: $BENCH_TOKENS"
  echo ""

  # Table header
  printf "  ${DIM}%-38s  %6s  %8s  %8s  %s${NC}\n" "MODEL" "MB" "PROMPT" "GEN" "STATUS"
  echo -e "  ${DIM}──────────────────────────────────────────────────────────${NC}"

  local total=${#models[@]}
  local done_count=0

  for model in "${models[@]}"; do
    (( done_count++ ))
    local name
    name=$(basename "$model" .gguf)
    printf "  ${DIM}[%d/%d]${NC} %-36s ... " "$done_count" "$total" "${name:0:36}"

    local result
    result=$(bench_model "$model")

    IFS='|' read -r rname rmb rprompt rgen relapsed rclass <<< "$result"
    local cc=$GREEN
    [[ "$rclass" == "CAUTION" || "$rclass" == "RISKY" ]] && cc=$YELLOW
    [[ "$rclass" == "SKIPPED" || "$rclass" == "UNSAFE" ]] && cc=$RED
    printf "${cc}gen=%-6s${NC}  prompt=%-6s  %s\n" "$rgen" "$rprompt" "$relapsed"
  done

  show_results_table
}

run_bench "$@"
