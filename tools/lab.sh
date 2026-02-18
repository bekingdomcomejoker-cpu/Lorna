#!/bin/bash
# ============================================================
# LORNA v3 Enterprise — tools/lab.sh
# Complete benchmark lab (from DSBench.pdf verified tests)
# Integrates: RAM mapping, context ceiling, thread tuning,
# persistent memory, exhaustive parameter sweep
# ============================================================

LORNA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$LORNA_DIR/lib/core.sh"
source "$LORNA_DIR/lib/memory.sh"
source "$LORNA_DIR/lib/registry.sh"

LAB_LOG="$HOME/lorna_lab_results_$(date +%Y%m%d_%H%M%S).txt"

run_lab() {
  lorna_banner
  echo -e "  ${BOLD}MODE: FULL BENCHMARK LAB${NC}"
  echo -e "  ${DIM}Complete parameter sweep with RAM monitoring${NC}"
  echo -e "  ${DIM}Based on DSBench.pdf verified methodology${NC}"
  echo ""

  # Select model
  rm -f "$LORNA_TMP/menu_models"
  local count
  count=$(build_model_menu)
  echo "" >&2

  read -rp "  Select model for lab testing [1-$count]: " selection
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
  ok "Lab testing: $name (${size_mb}MB)"
  echo ""

  # Define test matrix (from verified DSBench data)
  local contexts=(512 1024 2048 4096 8192)
  local threads=(2 3 4 5)
  local batches=(16 32 64 128)
  local temps=(0.1 0.2 0.3 0.5 0.7)

  local total_tests=$(( ${#contexts[@]} * ${#threads[@]} * ${#batches[@]} * ${#temps[@]} ))
  
  warn "This will run $total_tests tests. Continue? [y/N]"
  read -rp "  > " confirm
  [[ "${confirm,,}" != "y" ]] && return 0

  # Initialize lab log
  {
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║           LORNA BENCHMARK LAB — FULL SWEEP                ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    echo "Model: $name (${size_mb}MB)"
    echo "Device: Redmi 13C (4GB RAM)"
    echo "Timestamp: $(date)"
    echo "Total tests: $total_tests"
    echo ""
    printf "%-6s %-6s %-6s %-6s %-8s %-10s %-10s %-8s %-8s %-8s %s\n" \
      "CTX" "THR" "BATCH" "TEMP" "TIME" "PROMPT" "GEN" "RAM_MB" "SWAP_MB" "RESULT" "NOTES"
    echo "════════════════════════════════════════════════════════════════════════════════════"
  } > "$LAB_LOG"

  local test_num=0
  local best_config="" best_tps=0

  for ctx in "${contexts[@]}"; do
    for thr in "${threads[@]}"; do
      for batch in "${batches[@]}"; do
        for temp in "${temps[@]}"; do
          (( test_num++ ))

          printf "  ${DIM}[%4d/%4d]${NC} ctx=%-5s t=%-2s b=%-4s temp=%-4s " \
            "$test_num" "$total_tests" "$ctx" "$thr" "$batch" "$temp"

          # RAM before
          local ram_before swap_before
          ram_before=$(awk '/^MemAvailable/{print int($2/1024)}' /proc/meminfo || echo 2000)
          swap_before=$(awk 'BEGIN{t=0;f=0}/^SwapTotal/{t=$2}/^SwapFree/{f=$2}END{print int((t-f)/1024)}' /proc/meminfo || echo 0)

          # Test prompt (from DSBench.pdf)
          echo "Explain the convergence of the p-series and relate it to the Riemann zeta function." \
            > "$LORNA_TMP/lab_prompt.txt"

          # Run test
          local start_ms end_ms
          start_ms=$(date +%s%3N)

          "$LLAMA_BIN" \
            -m "$model" \
            -f "$LORNA_TMP/lab_prompt.txt" \
            -n 400 \
            -c "$ctx" \
            -t "$thr" \
            -b "$batch" \
            --temp "$temp" \
            --mmap \
            --no-display-prompt \
            --no-warmup \
            2>"$LORNA_TMP/lab_stderr.txt" > "$LORNA_TMP/lab_stdout.txt" < /dev/null

          local exit_code=$?
          end_ms=$(date +%s%3N)
          local elapsed_ms=$(( end_ms - start_ms ))
          local elapsed_s=$(awk "BEGIN{printf \"%.2f\", $elapsed_ms/1000}")

          # RAM after
          local ram_after swap_after
          ram_after=$(awk '/^MemAvailable/{print int($2/1024)}' /proc/meminfo || echo 1900)
          swap_after=$(awk 'BEGIN{t=0;f=0}/^SwapTotal/{t=$2}/^SwapFree/{f=$2}END{print int((t-f)/1024)}' /proc/meminfo || echo 0)

          local ram_delta=$(( ram_before - ram_after ))
          local swap_delta=$(( swap_after - swap_before ))

          # Parse t/s
          local prompt_tps="" gen_tps="" result="" notes=""
          
          if [[ "$exit_code" -eq 0 ]]; then
            prompt_tps=$(grep -oE '[0-9]+\.[0-9]+[[:space:]]+tokens per second' "$LORNA_TMP/lab_stderr.txt" 2>/dev/null \
              | head -1 | grep -oE '^[0-9]+\.[0-9]+' || echo "?")
            gen_tps=$(grep -oE '[0-9]+\.[0-9]+[[:space:]]+tokens per second' "$LORNA_TMP/lab_stderr.txt" 2>/dev/null \
              | tail -1 | grep -oE '^[0-9]+\.[0-9]+' || echo "?")
            result="OK"
            
            # Track best
            if [[ "$gen_tps" != "?" ]] && (( $(awk "BEGIN{print ($gen_tps > $best_tps)}") )); then
              best_tps=$gen_tps
              best_config="ctx=$ctx t=$thr b=$batch temp=$temp"
            fi

            # Add notes for exceptional configs
            if (( swap_delta > 200 )); then
              notes="HIGH_SWAP"
            elif [[ "$gen_tps" != "?" ]] && (( $(awk "BEGIN{print ($gen_tps > 5.0)}") )); then
              notes="FAST"
            fi

            echo -e "${GREEN}${gen_tps}t/s${NC}"
          else
            result="CRASH"
            prompt_tps="?"
            gen_tps="?"
            notes="OOM_KILL"
            echo -e "${RED}CRASH${NC}"
          fi

          # Log to file
          printf "%-6s %-6s %-6s %-6s %-8s %-10s %-10s %-8s %-8s %-8s %s\n" \
            "$ctx" "$thr" "$batch" "$temp" "${elapsed_s}s" "$prompt_tps" "$gen_tps" \
            "$ram_delta" "$swap_delta" "$result" "$notes" >> "$LAB_LOG"

          # Brief cooldown
          sleep 1
        done
      done
    done
  done

  # Generate summary
  {
    echo ""
    echo "════════════════════════════════════════════════════════════════════════════════════"
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                    LAB SUMMARY                             ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    echo "Best configuration found:"
    echo "  $best_config → ${best_tps} t/s"
    echo ""
    echo "Analysis:"
    echo ""
    
    # Find optimal context
    local optimal_ctx=$(grep -v "CRASH" "$LAB_LOG" | awk '{print $1}' | sort -rn | head -1)
    echo "  • Max stable context: ${optimal_ctx}"
    
    # Find optimal threads
    local optimal_thr=$(grep "FAST" "$LAB_LOG" | awk '{print $2}' | sort | uniq -c | sort -rn | head -1 | awk '{print $2}')
    [[ -z "$optimal_thr" ]] && optimal_thr=$(grep -v "CRASH" "$LAB_LOG" | awk '{print $2}' | sort | uniq -c | sort -rn | head -1 | awk '{print $2}')
    echo "  • Optimal threads: ${optimal_thr}"
    
    # RAM pressure analysis
    local avg_ram=$(grep -v "CRASH\|CTX" "$LAB_LOG" | awk '{sum+=$8; count++} END {printf "%.0f", sum/count}')
    echo "  • Average RAM usage: ${avg_ram}MB per run"
    
    echo ""
    echo "Recommendations:"
    echo ""
    echo "  Daily driver preset:"
    echo "    lorna config $name --ctx 4096 --threads 3 --batch 32 --temp 0.3"
    echo ""
    echo "  Speed preset:"
    echo "    lorna config $name --ctx 2048 --threads 4 --batch 64 --temp 0.5"
    echo ""
  } >> "$LAB_LOG"

  echo ""
  echo -e "${GREEN}${BOLD}  ═══════════════════════════════════════════${NC}"
  echo -e "${GREEN}${BOLD}  ✓ LAB COMPLETE${NC}"
  echo -e "${GREEN}${BOLD}  ═══════════════════════════════════════════${NC}"
  echo ""
  ok "Full results: $LAB_LOG"
  echo ""
  info "Best config: ${GOLD}$best_config${NC} → ${BOLD}${best_tps} t/s${NC}"
  echo ""

  # Offer to save best config
  read -rp "  Save best config for this model? [Y/n]: " save_confirm
  if [[ "${save_confirm,,}" != "n" ]]; then
    mkdir -p "$HOME/.lorna_configs"
    local config_file="$HOME/.lorna_configs/$(basename "$model" .gguf).conf"
    
    read -r ctx thr batch temp <<< $(echo "$best_config" | sed 's/ctx=\([0-9]*\) t=\([0-9]*\) b=\([0-9]*\) temp=\([0-9.]*\)/\1 \2 \3 \4/')
    
    cat > "$config_file" << CONF
# Auto-generated optimal config for $(basename "$model" .gguf)
# Generated: $(date)
# Best measured: ${best_tps} t/s
LORNA_CTX=$ctx
LORNA_THREADS=$thr
LORNA_BATCH=$batch
LORNA_TEMP=$temp
CONF
    ok "Config saved: $config_file"
    info "This model will now use these settings automatically"
  fi

  log "LAB: $name | $total_tests tests | Best: $best_config @ ${best_tps}t/s | Log: $LAB_LOG"
}

run_lab "$@"
