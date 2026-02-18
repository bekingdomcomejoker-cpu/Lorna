#!/bin/bash
# ============================================================
# LORNA — pipelines/race.sh  (v2 — all bugs fixed)
# Run N models on same prompt. Tiny models (≤300MB) run in
# parallel; larger ones auto-degrade to sequential.
# ============================================================

LORNA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$LORNA_DIR/lib/core.sh"
source "$LORNA_DIR/lib/memory.sh"
source "$LORNA_DIR/lib/registry.sh"

TMP_DIR="$LORNA_TMP/race"
mkdir -p "$TMP_DIR"

run_race() {
  local n_models="${1:-3}"
  (( n_models > 5 )) && { warn "Capping at 5 simultaneous models"; n_models=5; }

  lorna_banner
  echo -e "  ${BOLD}MODE: RACE — Simultaneous Model Battle${NC}"
  echo -e "  ${DIM}Same prompt → N models → compare outputs side-by-side${NC}"
  echo ""
  print_ram_status
  echo ""

  read -rp "  Enter prompt: " USER_INPUT
  [[ -z "$USER_INPUT" ]] && { err "No input."; return 1; }
  echo ""

  # Gather all top-10 paths
  local all_paths=()
  while IFS= read -r path; do
    all_paths+=("$path")
  done < <(get_top_n_paths 10)

  if (( ${#all_paths[@]} == 0 )); then
    err "No models found."
    return 1
  fi

  # BUG FIXED: separate safe vs fallback clearly, then build the
  # final list — don't mix them and then keep use_parallel=true
  local parallel_models=()
  local sequential_models=()

  for path in "${all_paths[@]}"; do
    if is_parallel_safe "$path"; then
      (( ${#parallel_models[@]} < n_models )) && parallel_models+=("$path")
    else
      sequential_models+=("$path")
    fi
  done

  # Fill remaining slots with sequential models if not enough tiny ones
  local needed=$(( n_models - ${#parallel_models[@]} ))
  local seq_fill=()
  for (( i=0; i<needed && i<${#sequential_models[@]}; i++ )); do
    seq_fill+=("${sequential_models[$i]}")
  done

  # The final ordered list: parallel first, then sequential top-ups
  local final_models=("${parallel_models[@]}" "${seq_fill[@]}")
  local actual_count=${#final_models[@]}

  if (( actual_count == 0 )); then
    err "No models available."
    return 1
  fi

  local n_parallel=${#parallel_models[@]}
  local n_sequential=${#seq_fill[@]}

  if (( n_parallel > 0 )); then
    info "${n_parallel} model(s) running ${BOLD}simultaneously${NC} (≤300MB)"
  fi
  if (( n_sequential > 0 )); then
    info "${n_sequential} larger model(s) running ${BOLD}sequentially${NC} after"
  fi
  echo ""

  local prompt_file="$TMP_DIR/shared_prompt.txt"
  echo "$USER_INPUT" > "$prompt_file"

  local pids=()
  local start_time=$(date +%s)

  # ─── LAUNCH PARALLEL BATCH ──────────────────────────────
  for (( i=0; i<n_parallel; i++ )); do
    local model="${final_models[$i]}"
    local name size_mb
    name=$(basename "$model" .gguf)
    size_mb=$(du -m "$model" | cut -f1)
    info "Launching [PARALLEL] #$(( i+1 )): $name (${size_mb}MB)"
    run_model "$model" "$prompt_file" "$TMP_DIR/output_${i}.txt" 96 &
    pids+=($!)
  done

  # Wait for all parallel jobs
  if (( n_parallel > 0 )); then
    echo ""
    info "Waiting for parallel models..."
    for pid in "${pids[@]}"; do
      wait "$pid" 2>/dev/null || true
    done
    ok "Parallel phase complete"
  fi

  # ─── LAUNCH SEQUENTIAL TOP-UPS ──────────────────────────
  for (( j=0; j<n_sequential; j++ )); do
    local idx=$(( n_parallel + j ))
    local model="${final_models[$idx]}"
    local name size_mb
    name=$(basename "$model" .gguf)
    size_mb=$(du -m "$model" | cut -f1)

    local class
    class=$(model_load_class "$model")
    if [[ "$class" == "UNSAFE" ]]; then
      warn "#$(( idx+1 )) $name: UNSAFE RAM — skipping"
      continue
    fi

    if (( j > 0 )); then
      echo -e "  ${DIM}Memory gap: 2s...${NC}"
      sleep 2; sync 2>/dev/null
    fi
    info "Launching [SEQUENTIAL] #$(( idx+1 )): $name (${size_mb}MB)"
    run_model "$model" "$prompt_file" "$TMP_DIR/output_${idx}.txt" 96
    pids+=(0)
  done

  local total_time=$(( $(date +%s) - start_time ))

  # ─── DISPLAY ALL RESULTS ────────────────────────────────
  echo ""
  echo -e "${CYAN}${BOLD}  ╔═══════════════════════════════════════════════╗${NC}"
  echo -e "${CYAN}${BOLD}  ║   RACE RESULTS — ${actual_count} models  /  ${total_time}s total       ║${NC}"
  echo -e "${CYAN}${BOLD}  ╚═══════════════════════════════════════════════╝${NC}"

  for (( i=0; i<actual_count; i++ )); do
    local model="${final_models[$i]}"
    local name size_mb
    name=$(basename "$model" .gguf)
    size_mb=$(du -m "$model" | cut -f1)
    local output_file="$TMP_DIR/output_${i}.txt"
    local mode_tag="PARALLEL"
    (( i >= n_parallel )) && mode_tag="SEQUENTIAL"

    echo ""
    echo -e "${GOLD}  ┌─ #$(( i+1 )) ${mode_tag} · ${name:0:38} (${size_mb}MB) ─${NC}"

    if [[ -s "$output_file" ]]; then
      sed 's/^/     /' "$output_file" | head -20
    else
      echo -e "${RED}     [no output — possibly OOM-killed or model missing]${NC}"
    fi
    echo -e "${DIM}  └──────────────────────────────────────────────────────${NC}"
  done

  echo ""
  echo -e "${GREEN}  ✓ Race complete — $actual_count models, ${total_time}s${NC}"
  log "RACE: $actual_count models (${n_parallel} parallel, ${n_sequential} sequential) in ${total_time}s"
}

run_race "$@"
