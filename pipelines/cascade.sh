#!/bin/bash
# ============================================================
# LORNA — pipelines/cascade.sh  (v2 — all bugs fixed)
# Historical Reflex → Oracle → Warfare (Context Seizure)
# Qwen 0.5B → Gemma/R1 → DeepSeek Coder
#
# BUG FIXED: Falls back to ANY suitable model found on device
# rather than failing if exact filenames don't match.
# ============================================================

LORNA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$LORNA_DIR/lib/core.sh"
source "$LORNA_DIR/lib/memory.sh"
source "$LORNA_DIR/lib/registry.sh"

TMP_DIR="$LORNA_TMP/cascade"
mkdir -p "$TMP_DIR"

# ─── SMART MODEL FINDER ─────────────────────────────────────
# find_best_model <role> <preferred_kw1> [<preferred_kw2> ...]
# If no keyword match, falls back to smallest available model (role=reflex/oracle)
# or any model (role=warfare)
find_best_model() {
  local role="$1"; shift
  local keywords=("$@")

  # Try keyword matches first
  for kw in "${keywords[@]}"; do
    local found
    found=$(find ~ -type f -iname "*${kw}*.gguf" ! -path "*/backups/*" -size +50M 2>/dev/null | head -1)
    [[ -n "$found" ]] && echo "$found" && return 0
  done

  # Fallback strategy by role
  case "$role" in
    reflex)
      # Smallest model on device — fastest, used for cleanup
      find ~ -type f -name "*.gguf" ! -name "ggml-vocab-*" \
        ! -path "*/backups/*" -size +50M 2>/dev/null \
        | xargs -I{} sh -c 'echo "$(du -m "{}" 2>/dev/null | cut -f1) {}"' 2>/dev/null \
        | sort -n | head -1 | awk '{print $2}'
      ;;
    oracle)
      # Medium model — something over 400MB but not coder-specific
      find ~ -type f -name "*.gguf" ! -name "ggml-vocab-*" \
        ! -path "*/backups/*" -size +400M 2>/dev/null | head -1
      ;;
    warfare)
      # Any model — deepseek coder preferred, already tried via keyword
      scan_all_models | tail -1
      ;;
  esac
}

run_cascade() {
  lorna_banner
  echo -e "  ${BOLD}MODE: CASCADE — Context Seizure Architecture${NC}"
  echo -e "  ${DIM}Reflex → Oracle → Warfare${NC}"
  echo -e "  ${DIM}Qwen 0.5B → Gemma/R1 → DeepSeek Coder${NC}"
  echo ""
  print_ram_status
  echo ""

  # ─── RESOLVE NODES ──────────────────────────────────────
  local REFLEX ORACLE WARFARE

  REFLEX=$(find_best_model "reflex" \
    "qwen2.5-0.5b-instruct" "qwen-sentinel" "smollm2-360m" "smollm-360m" "ernie")

  ORACLE=$(find_best_model "oracle" \
    "gemma-2-2b" "gemma-2b" "deepseek-r1-distill" "llama-3.2-1b" "qwen2.5-1.5b")

  WARFARE=$(find_best_model "warfare" \
    "deepseek-coder-1.3b" "deepseek-coder" "deepseek-coder-1b")

  # ─── SHOW RESOLUTION ────────────────────────────────────
  echo -e "  ${BOLD}Node resolution:${NC}"
  if [[ -n "$REFLEX"  && -f "$REFLEX"  ]]; then ok  "REFLEX:  $(basename "$REFLEX")"
  else                                            warn "REFLEX:  not found — Node 0 will be skipped"; REFLEX=""; fi

  if [[ -n "$ORACLE"  && -f "$ORACLE"  ]]; then ok  "ORACLE:  $(basename "$ORACLE")"
  else                                            warn "ORACLE:  not found — Node 1 will be skipped"; ORACLE=""; fi

  if [[ -n "$WARFARE" && -f "$WARFARE" ]]; then ok  "WARFARE: $(basename "$WARFARE")"
  else                                            warn "WARFARE: not found — Node 2 will be skipped"; WARFARE=""; fi

  # At least one of Oracle/Warfare must be present to be useful
  if [[ -z "$ORACLE" && -z "$WARFARE" ]]; then
    err "Need at least ORACLE or WARFARE model. Run 'lorna health' to see what's on device."
    return 1
  fi

  echo ""

  # RAM check
  local free_ram
  free_ram=$(get_free_ram_mb)
  if (( free_ram < 400 )); then
    warn "Low RAM (${free_ram}MB) — cleaning zombie processes..."
    cleanup_llama
    wait_for_memory_recovery 400
    info "RAM after cleanup: $(get_free_ram_mb)MB"
  fi

  echo ""
  read -rp "  Enter Goal: " USER_INPUT
  [[ -z "$USER_INPUT" ]] && { err "No input."; return 1; }

  local cascade_start=$(date +%s)
  log "CASCADE START | $USER_INPUT"

  # ═══════════════════════════════════════════════════════
  # NODE 0 — REFLEX
  # ═══════════════════════════════════════════════════════
  local STRUCT="$USER_INPUT"

  if [[ -n "$REFLEX" ]]; then
    node_header "0" "REFLEX — $(basename "$REFLEX" .gguf | tr '[:lower:]' '[:upper:]')"

    printf 'Rewrite clearly and concisely (max 80 words):\n%s\n' "$USER_INPUT" \
      > "$TMP_DIR/reflex.txt"

    run_model "$REFLEX" "$TMP_DIR/reflex.txt" "$TMP_DIR/reflex_out.txt" 96 "0.6"

    local reflex_raw
    reflex_raw=$(cat "$TMP_DIR/reflex_out.txt" 2>/dev/null)
    if [[ -n "$reflex_raw" ]]; then
      STRUCT="$reflex_raw"
      echo "$STRUCT"
    else
      warn "Reflex returned empty — using raw input"
    fi
    node_footer
    sleep 1; sync 2>/dev/null
  fi

  # ═══════════════════════════════════════════════════════
  # NODE 1 — ORACLE
  # ═══════════════════════════════════════════════════════
  local PLAN="$STRUCT"

  if [[ -n "$ORACLE" ]]; then
    node_header "1" "ORACLE — $(basename "$ORACLE" .gguf | tr '[:lower:]' '[:upper:]')"

    local oracle_lc
    oracle_lc=$(basename "$ORACLE" .gguf | tr '[:upper:]' '[:lower:]')

    # Apply model-family-specific prompt format
    if [[ "$oracle_lc" == *"gemma"* ]]; then
      printf '<start_of_turn>user\nAnalyze from first principles in 3 concise steps:\n%s\n<start_of_turn>model\n' \
        "$STRUCT" > "$TMP_DIR/oracle.txt"
    elif [[ "$oracle_lc" == *"deepseek"* ]]; then
      printf '### Instruction:\nAnalyze from first principles in 3 concise steps:\n%s\n### Response:\n' \
        "$STRUCT" > "$TMP_DIR/oracle.txt"
    elif [[ "$oracle_lc" == *"llama"* ]]; then
      printf '<|begin_of_text|><|start_header_id|>user<|end_header_id|>\nAnalyze in 3 concise steps:\n%s<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n' \
        "$STRUCT" > "$TMP_DIR/oracle.txt"
    elif [[ "$oracle_lc" == *"qwen"* ]]; then
      printf '<|im_start|>user\nAnalyze in 3 concise steps:\n%s\n<|im_end|>\n<|im_start|>assistant\n' \
        "$STRUCT" > "$TMP_DIR/oracle.txt"
    else
      printf 'Analyze from first principles in 3 concise steps:\n%s\n' \
        "$STRUCT" > "$TMP_DIR/oracle.txt"
    fi

    run_model "$ORACLE" "$TMP_DIR/oracle.txt" "$TMP_DIR/oracle_out.txt" 200 "0.3"

    local oracle_raw
    oracle_raw=$(cat "$TMP_DIR/oracle_out.txt" 2>/dev/null)
    if [[ -n "$oracle_raw" ]]; then
      # Context Seizure: compress to 40 lines max before passing forward
      PLAN=$(compress_output "$oracle_raw" 40)
      echo "$PLAN"
    else
      warn "Oracle returned empty — passing structured input to Warfare"
    fi

    node_footer
    sleep 2; sync 2>/dev/null
    wait_for_memory_recovery 300
  fi

  # ═══════════════════════════════════════════════════════
  # NODE 2 — WARFARE
  # ═══════════════════════════════════════════════════════
  if [[ -n "$WARFARE" ]]; then
    node_header "2" "WARFARE — $(basename "$WARFARE" .gguf | tr '[:lower:]' '[:upper:]')"

    # DeepSeek Coder requires strict ### format — lesson from all PDF logs
    printf '### Instruction:\nWrite executable Python code to solve: %s\n\n### Context:\n%s\n\n### Response:\n' \
      "$USER_INPUT" "$PLAN" > "$TMP_DIR/warfare.txt"

    run_model "$WARFARE" "$TMP_DIR/warfare.txt" "$TMP_DIR/warfare_out.txt" 300 "0.2"

    local warfare_raw
    warfare_raw=$(cat "$TMP_DIR/warfare_out.txt" 2>/dev/null)
    if [[ -n "$warfare_raw" ]]; then
      echo "$warfare_raw"
    else
      warn "Warfare returned empty."
    fi
    node_footer
  fi

  local total_time=$(( $(date +%s) - cascade_start ))
  echo ""
  echo -e "${GREEN}${BOLD}  ═══════════════════════════════════════════${NC}"
  echo -e "${GREEN}${BOLD}  ✓ CASCADE COMPLETE — ${total_time}s${NC}"
  echo -e "${GREEN}${BOLD}  ═══════════════════════════════════════════${NC}"
  log "CASCADE END | ${total_time}s"
}

run_cascade "$@"
