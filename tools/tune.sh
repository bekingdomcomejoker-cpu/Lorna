#!/bin/bash
# ============================================================
# LORNA v3 — tools/tune.sh
# Comprehensive Parameter Tuning Lab
# Tests all combinations: context, threads, batch, temp
# Based on DeepSeek R1 benchmark data showing 5.0 t/s @ 4GB
# ============================================================

LORNA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$LORNA_DIR/lib/core.sh"
source "$LORNA_DIR/lib/memory.sh"
source "$LORNA_DIR/lib/registry.sh"

RESULTS_FILE="$HOME/lorna_tune_results_$(date +%Y%m%d_%H%M%S).txt"
TEST_PROMPT="Explain the convergence of the p-series and relate it to the Riemann zeta function."

run_tune() {
  local mode="${1:-quick}"
  
  lorna_banner
  echo -e "  ${BOLD}MODE: PARAMETER TUNING LAB${NC}"
  echo -e "  ${DIM}Systematic parameter sweep with RAM monitoring${NC}"
  echo ""

  # Select model
  rm -f "$LORNA_TMP/menu_models"
  local count
  count=$(build_model_menu)
  echo "" >&2

  if (( count == 0 )); then
    err "No models found"
    return 1
  fi

  read -rp "  Select model to tune [1-$count]: " selection
  local model
  model=$(select_model "$selection")

  if [[ -z "$model" || ! -f "$model" ]]; then
    err "Invalid selection"
    return 1
  fi

  local name size_mb
  name=$(basename "$model" .gguf)
  size_mb=$(du -m "$model" | cut -f1)

  echo ""
  ok "Tuning: $name (${size_mb}MB)"
  echo ""

  # Define test matrices based on mode
  local contexts threads batches temps

  case "$mode" in
    quick)
      contexts=(512 1024 2048)
      threads=(2 3 4)
      batches=(32 64)
      temps=(0.2 0.5)
      info "Quick mode: 3 contexts × 3 threads × 2 batches × 2 temps = 36 tests"
      ;;
    full)
      contexts=(512 1024 2048 4096 8192)
      threads=(2 3 4 5)
      batches=(16 32 64 128)
      temps=(0.1 0.3 0.5 0.7)
      info "Full mode: 5 contexts × 4 threads × 4 batches × 4 temps = 320 tests"
      warn "This will take 30+ minutes. Continue? [y/N]"
      read -rp "  > " confirm
      [[ "${confirm,,}" != "y" ]] && return 0
      ;;
    custom)
      read -rp "  Contexts (space-separated, e.g. 1024 2048 4096): " ctx_input
      read -rp "  Threads (e.g. 2 3 4): " thr_input
      read -rp "  Batch sizes (e.g. 32 64): " batch_input
      read -rp "  Temperatures (e.g. 0.2 0.5): " temp_input
      contexts=($ctx_input)
      threads=($thr_input)
      batches=($batch_input)
      temps=($temp_input)
      ;;
  esac

  local total_tests=$(( ${#contexts[@]} * ${#threads[@]} * ${#batches[@]} * ${#temps[@]} ))
  echo ""
  info "Starting $total_tests tests..."
  echo ""

  # Initialize results file
  {
    echo "=== LORNA Parameter Tuning Lab ==="
    echo "Model: $name (${size_mb}MB)"
    echo "Test prompt: $TEST_PROMPT"
    echo "Timestamp: $(date)"
    echo "Total tests: $total_tests"
    echo ""
    printf "%-6s %-8s %-8s %-6s %-6s %-10s %-10s %-8s %-8s %-8s\n" \
      "CTX" "THREADS" "BATCH" "TEMP" "TIME" "PROMPT_TPS" "GEN_TPS" "RAM_MB" "SWAP_MB" "STATUS"
    echo "─────────────────────────────────────────────────────────────────────────────────────"
  } > "$RESULTS_FILE"

  local test_num=0
  local best_gen_tps=0
  local best_config=""

  for ctx in "${contexts[@]}"; do
    for thr in "${threads[@]}"; do
      for batch in "${batches[@]}"; do
        for temp in "${temps[@]}"; do
          (( test_num++ ))
          
          printf "  ${DIM}[%3d/%3d]${NC} Testing: ctx=%-5s t=%-2s b=%-4s temp=%-4s ... " \
            "$test_num" "$total_tests" "$ctx" "$thr" "$batch" "$temp"

          # RAM before
          local ram_before swap_before
          ram_before=$(awk '/^MemAvailable/{print int($2/1024)}' /proc/meminfo)
          swap_before=$(awk 'BEGIN{t=0;f=0}/^SwapTotal/{t=$2}/^SwapFree/{f=$2}END{print int((t-f)/1024)}' /proc/meminfo)

          # Create temp prompt file
          echo "$TEST_PROMPT" > "$LORNA_TMP/tune_prompt.txt"

          # Run test
          local start_ms end_ms
          start_ms=$(date +%s%3N)

          "$LLAMA_BIN" \
            -m "$model" \
            -f "$LORNA_TMP/tune_prompt.txt" \
            -n 100 \
            -c "$ctx" \
            -t "$thr" \
            -b "$batch" \
            --temp "$temp" \
            --no-display-prompt \
            2>"$LORNA_TMP/tune_stderr.txt" > "$LORNA_TMP/tune_stdout.txt" < /dev/null

          local exit_code=$?
          end_ms=$(date +%s%3N)
          local elapsed_ms=$(( end_ms - start_ms ))
          local elapsed_s=$(awk "BEGIN{printf \"%.2f\", $elapsed_ms/1000}")

          # RAM after
          local ram_after swap_after
          ram_after=$(awk '/^MemAvailable/{print int($2/1024)}' /proc/meminfo)
          swap_after=$(awk 'BEGIN{t=0;f=0}/^SwapTotal/{t=$2}/^SwapFree/{f=$2}END{print int((t-f)/1024)}' /proc/meminfo)

          local ram_used=$(( ram_before - ram_after ))
          local swap_used=$(( swap_after - swap_before ))

          # Parse t/s from stderr
          local prompt_tps gen_tps status
          if [[ "$exit_code" -eq 0 ]]; then
            prompt_tps=$(grep -oE '[0-9]+\.[0-9]+[[:space:]]+tokens per second' "$LORNA_TMP/tune_stderr.txt" 2>/dev/null \
              | head -1 | grep -oE '^[0-9]+\.[0-9]+' || echo "?")
            gen_tps=$(grep -oE '[0-9]+\.[0-9]+[[:space:]]+tokens per second' "$LORNA_TMP/tune_stderr.txt" 2>/dev/null \
              | tail -1 | grep -oE '^[0-9]+\.[0-9]+' || echo "?")
            status="OK"
            
            # Track best config
            if [[ "$gen_tps" != "?" ]] && (( $(awk "BEGIN{print ($gen_tps > $best_gen_tps)}") )); then
              best_gen_tps=$gen_tps
              best_config="ctx=$ctx t=$thr b=$batch temp=$temp"
            fi

            echo -e "${GREEN}${gen_tps}t/s${NC}"
          else
            prompt_tps="?"
            gen_tps="?"
            status="CRASH"
            echo -e "${RED}CRASH${NC}"
          fi

          # Log to file
          printf "%-6s %-8s %-8s %-6s %-6s %-10s %-10s %-8s %-8s %-8s\n" \
            "$ctx" "$thr" "$batch" "$temp" "${elapsed_s}s" "$prompt_tps" "$gen_tps" \
            "$ram_used" "$swap_used" "$status" >> "$RESULTS_FILE"

          # Brief cooldown
          sleep 1
        done
      done
    done
  done

  # Summary
  echo ""
  echo -e "${GREEN}${BOLD}  ═══════════════════════════════════════════${NC}"
  echo -e "${GREEN}${BOLD}  ✓ TUNING COMPLETE${NC}"
  echo -e "${GREEN}${BOLD}  ═══════════════════════════════════════════${NC}"
  echo ""
  ok "Results saved: $RESULTS_FILE"
  echo ""
  info "Best configuration found:"
  echo -e "  ${GOLD}$best_config${NC} → ${BOLD}${best_gen_tps} t/s${NC}"
  echo ""
  info "To apply this config permanently:"
  echo -e "  ${CYAN}lorna config $(basename "$model" .gguf) --apply-best${NC}"
  echo ""

  log "TUNE: $name | $total_tests tests | Best: $best_config @ ${best_gen_tps}t/s"
}

run_tune "$@"
