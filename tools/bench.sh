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
# Every benchmark process is non-interactive: it receives /exit on stdin and
# has a hard deadline, so no model can remain waiting for a follow-up reply.
BENCH_EXIT_INPUT="/exit"
BENCH_TIMEOUT_SECONDS="${LORNA_BENCH_TIMEOUT_SECONDS:-180}"
BENCH_LOCK_DIR="$LORNA_TMP/bench.lock"

mkdir -p "$TMP_DIR"

# ─── SINGLE-RUN LOCK ─────────────────────────────────────────
# Concurrent benchmarks would compete for the same device memory, temporary
# files, and leaderboard.  Keep exactly one active run and recover stale locks.
acquire_bench_lock() {
  if mkdir "$BENCH_LOCK_DIR" 2>/dev/null; then
    printf '%s\n' "$$" > "$BENCH_LOCK_DIR/pid"
    return 0
  fi

  local owner=""
  [[ -f "$BENCH_LOCK_DIR/pid" ]] && owner=$(cat "$BENCH_LOCK_DIR/pid" 2>/dev/null)
  if [[ "$owner" =~ ^[0-9]+$ ]] && kill -0 "$owner" 2>/dev/null; then
    err "A Lorna benchmark is already running (PID $owner). Wait for it to finish."
    return 1
  fi

  rm -rf "$BENCH_LOCK_DIR"
  mkdir "$BENCH_LOCK_DIR" || return 1
  printf '%s\n' "$$" > "$BENCH_LOCK_DIR/pid"
}

release_bench_lock() {
  rm -rf "$BENCH_LOCK_DIR"
}

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

  # Always emit six fields and persist the row, including a skip.  This keeps
  # the terminal status and the saved leaderboard consistent.
  if [[ "$class" == "UNSAFE" ]]; then
    local skipped_line="${name}|${size_mb}|?|?|0ms|SKIPPED"
    echo "$skipped_line"
    echo "$skipped_line" >> "$RESULTS_FILE"
    return 0
  fi

  echo "$BENCH_PROMPT" > "$TMP_DIR/bench_prompt.txt"

  # Benchmark with the same conservative tier settings used by Lorna itself.
  # Calling llama-cli with its defaults can allocate an oversized context on a
  # 4 GB device, leaving the benchmark on "Loading model..." or causing OOM.
  read -r ctx batch threads _ <<< "$(get_model_tier "$model")"
  probe_binary_flags
  local extra_flags=()
  [[ "$_LORNA_HAS_NO_WARMUP" -eq 1 ]] && extra_flags+=(--no-warmup)
  [[ "$_LORNA_HAS_CACHE_TYPE" -eq 1 ]] && extra_flags+=(--cache-type-k q4_0 --cache-type-v q4_0)

  local start_ms end_ms llama_status
  start_ms=$(date +%s%3N)
  # Feed /exit to this individual llama-cli process.  The token cap and
  # timeout remain as independent guards if a model ignores stdin.
  printf '%s\n' "$BENCH_EXIT_INPUT" | timeout "${BENCH_TIMEOUT_SECONDS}s" "$LLAMA_BIN" \
    -m "$model" \
    -f "$TMP_DIR/bench_prompt.txt" \
    -n "$BENCH_TOKENS" \
    -c "$ctx" \
    -t "$threads" \
    -b "$batch" \
    --temp 0.1 \
    --no-display-prompt \
    "${extra_flags[@]}" \
    2>"$TMP_DIR/bench_stderr.txt" > "$TMP_DIR/bench_stdout.txt"
  llama_status=${PIPESTATUS[1]}
  end_ms=$(date +%s%3N)
  local elapsed_ms=$(( end_ms - start_ms ))

  if (( llama_status != 0 )); then
    local failure_class="ERROR(${llama_status})"
    (( llama_status == 124 )) && failure_class="TIMEOUT"
    local error_line="${name}|${size_mb}|?|?|${elapsed_ms}ms|${failure_class}"
    echo "$error_line"
    echo "$error_line" >> "$RESULTS_FILE"
    cleanup_llama
    return 0
  fi

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

  acquire_bench_lock || return 1
  trap release_bench_lock EXIT INT TERM

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
      # "safe" means safe under the device's current RAM and swap pressure,
      # not merely smaller than an arbitrary file-size cutoff.
      while IFS= read -r path; do
        [[ "$(model_load_class "$path")" == "SAFE" ]] && models+=("$path")
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
    if [[ "$mode" == "safe" ]]; then
      err "No models are SAFE with the current RAM and swap pressure. Free memory, then retry the safe benchmark."
    else
      err "No models found."
    fi
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
    [[ "$rclass" == "SKIPPED" || "$rclass" == "UNSAFE" || "$rclass" == ERROR* ]] && cc=$RED
    printf "${cc}gen=%-6s${NC}  prompt=%-6s  %s\n" "$rgen" "$rprompt" "$relapsed"
  done

  show_results_table
}

run_bench "$@"
