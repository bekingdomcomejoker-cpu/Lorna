#!/bin/bash
# ============================================================
# LORNA — pipelines/chain.sh  (v2 — all bugs fixed)
# Chain 1–10 models: each passes compressed output to the next.
# Context Seizure pattern from historical TriLLM2 documents.
# ============================================================

LORNA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$LORNA_DIR/lib/core.sh"
source "$LORNA_DIR/lib/memory.sh"
source "$LORNA_DIR/lib/registry.sh"

TMP_DIR="$LORNA_TMP/chain"
mkdir -p "$TMP_DIR"

# BUG FIXED: declare inside function scope so it can't bleed
# between successive calls from the menu loop
_make_node_roles() {
  declare -gA NODE_ROLE=(
    [1]="REFLEX"
    [2]="BENCHMARK"
    [3]="FAST"
    [4]="RELAY"
    [5]="ORGANIZER"
    [6]="ANALYST"
    [7]="SENTINEL"
    [8]="PROCESSOR"
    [9]="ORACLE"
    [10]="WARFARE"
  )
}

get_node_instruction() {
  local position="$1" input="$4"
  case "$position" in
    first)  echo "Rewrite clearly and concisely (max 80 words): $input" ;;
    last)   printf "Present the following clearly and helpfully:\n%s" "$input" ;;
    *)      printf "Analyze and expand in 3 concise steps:\n%s" "$input" ;;
  esac
}

run_chain() {
  local n_models="${1:-2}"

  lorna_banner
  echo -e "  ${BOLD}MODE: CHAIN — ${n_models}-Model Pipeline${NC}"
  echo -e "  ${DIM}Each model receives compressed output of the previous${NC}"
  echo ""

  if (( n_models < 1 || n_models > 10 )); then
    err "Chain count must be 1–10"
    return 1
  fi

  print_ram_status
  echo ""

  read -rp "  Enter Goal: " USER_INPUT
  [[ -z "$USER_INPUT" ]] && { err "No input provided."; return 1; }
  echo ""

  # BUG FIXED: get_top_n_paths now uses fuzzy fallback so models
  # with different filenames still resolve
  local model_paths=()
  while IFS= read -r path; do
    model_paths+=("$path")
  done < <(get_top_n_paths "$n_models")

  if (( ${#model_paths[@]} == 0 )); then
    err "No models found. Ensure models are in ~/federation/models or ~/models"
    return 1
  fi

  local actual_count=${#model_paths[@]}
  if (( actual_count < n_models )); then
    warn "Only $actual_count of $n_models requested models found — proceeding with $actual_count"
    n_models=$actual_count
  fi

  _make_node_roles
  info "Starting chain: $n_models nodes"
  log "CHAIN START: $n_models nodes | Input: $USER_INPUT"

  local current_input="$USER_INPUT"
  local chain_start=$(date +%s)

  for (( i=0; i<n_models; i++ )); do
    local model="${model_paths[$i]}"
    local node_num=$(( i + 1 ))
    local role="${NODE_ROLE[$node_num]:-NODE${node_num}}"
    local name size_mb class
    name=$(basename "$model" .gguf)
    size_mb=$(du -m "$model" | cut -f1)
    class=$(model_load_class "$model")

    if [[ "$class" == "UNSAFE" ]]; then
      warn "Node $node_num ($name): UNSAFE RAM — skipping"
      log "CHAIN SKIP: Node $node_num $name"
      continue
    fi
    [[ "$class" == "RISKY" ]] && warn "Node $node_num: low RAM — proceeding carefully"

    node_header "$node_num" "${role} — ${name}"
    info "Model: $name (${size_mb}MB) | RAM: $(get_free_ram_mb)MB free"

    local position="middle"
    (( i == 0 ))          && position="first"
    (( i == n_models-1 )) && position="last"

    local prompt_file="$TMP_DIR/node${node_num}_prompt.txt"
    local output_file="$TMP_DIR/node${node_num}_output.txt"

    get_node_instruction "$position" "$node_num" "$n_models" "$current_input" > "$prompt_file"

    local n_tokens=128
    [[ "$position" == "first"  ]] && n_tokens=96
    [[ "$position" == "middle" ]] && n_tokens=200
    [[ "$position" == "last"   ]] && n_tokens=150
    (( size_mb > 700 )) && n_tokens=$(( n_tokens + 64 ))

    local node_start=$(date +%s)
    run_model "$model" "$prompt_file" "$output_file" "$n_tokens"
    local elapsed=$(( $(date +%s) - node_start ))

    local raw_output
    raw_output=$(cat "$output_file" 2>/dev/null)

    echo ""
    if [[ -z "$raw_output" ]]; then
      warn "Node $node_num: no output (possible OOM-kill)"
      log "CHAIN NODE $node_num: empty output"
    else
      echo "$raw_output"
      log "CHAIN NODE $node_num OK: ${#raw_output} chars in ${elapsed}s"
    fi

    node_footer
    echo -e "  ${DIM}Node ${node_num} elapsed: ${elapsed}s${NC}"

    # Context Seizure: compress before passing forward
    [[ -n "$raw_output" ]] && current_input=$(compress_output "$raw_output" 35)

    # Memory recovery gap between nodes
    if (( i < n_models - 1 )); then
      local next_size
      next_size=$(du -m "${model_paths[$((i+1))]}" 2>/dev/null | cut -f1)
      local gap=1
      (( next_size > 500  )) && gap=2
      (( next_size > 1000 )) && gap=3
      echo -e "  ${DIM}Memory cooldown: ${gap}s...${NC}"
      sleep "$gap"
      sync 2>/dev/null
    fi
  done

  local total_time=$(( $(date +%s) - chain_start ))
  echo ""
  echo -e "${GREEN}${BOLD}  ═══════════════════════════════════════════════${NC}"
  echo -e "${GREEN}${BOLD}  ✓ CHAIN COMPLETE — $n_models nodes in ${total_time}s${NC}"
  echo -e "${GREEN}${BOLD}  ═══════════════════════════════════════════════${NC}"
  log "CHAIN END: $n_models nodes, ${total_time}s"
}

run_chain "$@"
