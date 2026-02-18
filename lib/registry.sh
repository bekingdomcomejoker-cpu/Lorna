#!/bin/bash
# ============================================================
# LORNA — lib/registry.sh  (v2 — all bugs fixed)
# Top-10 registry, auto-scan, model menu
# ============================================================

# ─── TOP 10 KNOWN FILENAMES (ranked by generation speed) ────
declare -a LORNA_TOP10=(
  "1|Cerebras-111M|cerebras-111m.gguf"
  "2|NeoX-Tiny-125M|neox_tiny_125m.gguf"
  "3|node1_rwkv7|node1_rwkv7.gguf"
  "4|Tool-270M|tool-270m.gguf"
  "5|SmolLM2-360M-Alt|smollm2-360m-alt.gguf"
  "6|ERNIE-0.3B|ernie-0.3b.gguf"
  "7|Qwen-Sentinel|qwen-sentinel.gguf"
  "8|SmolLM-360M|smollm-360m.gguf"
  "9|Qwen2.5-0.5B-Instruct|qwen2.5-0.5b-instruct-q4_k_m.gguf"
  "10|Llama-3.2-1B-Instruct|llama-3.2-1b-instruct-q4_k_m.gguf"
)

# Additional known models beyond top 10
declare -a LORNA_EXTENDED=(
  "11|Qwen2.5-1.5B-Instruct|qwen2.5-1.5b-instruct-q4_k_m.gguf"
  "12|DeepSeek-R1-1.5B|deepseek-r1-distill-qwen-1.5b-q4_k_m.gguf"
  "13|DeepSeek-Coder-1.3B|deepseek-coder-1.3b-instruct-q4_k_m.gguf"
  "14|SmolLM-1.7B-Instruct|smollm-1.7b-instruct-q4_k_m.gguf"
  "15|Gemma-2-2B|gemma-2-2b-it-q4_k_m.gguf"
  "16|Dolphin-Phi-2|dolphin-2_6-phi-2.q4_k_m.gguf"
)

# ─── SCAN ALL REAL GGUF MODELS ON DEVICE ────────────────────
scan_all_models() {
  find ~ -type f -name "*.gguf" \
    ! -name "ggml-vocab-*"      \
    ! -name "*mmproj*"          \
    ! -path "*/backups/*"       \
    -size +50M                  \
    2>/dev/null | sort
}

# ─── RESOLVE TOP-10 PATHS ───────────────────────────────────
# BUG FIXED: now also does partial/fuzzy filename match so models
# with slightly different names (e.g. "Qwen2.5-0.5B-Q4_K_M.gguf")
# still resolve. Falls back to scan_all_models rank-ordered by size.
resolve_top10_paths() {
  # Step 1: try exact filename matches
  declare -A resolved

  for entry in "${LORNA_TOP10[@]}"; do
    IFS='|' read -r rank name filename <<< "$entry"
    local found
    found=$(find ~ -type f -iname "$filename" ! -path "*/backups/*" 2>/dev/null | head -1)
    [[ -n "$found" ]] && resolved["$rank"]="$found"
  done

  # Step 2: for any rank still missing, try fuzzy keyword match
  # e.g. rank 9 = Qwen2.5-0.5B-Instruct → search for files containing "qwen" and "0.5b"
  declare -a FUZZY_KEYWORDS=(
    "1|cerebras"
    "2|neox_tiny|neox-tiny"
    "3|rwkv7"
    "4|tool-270|tool_270"
    "5|smollm2-360|smollm2_360"
    "6|ernie"
    "7|qwen-sentinel|qwen_sentinel"
    "8|smollm-360|smollm_360"
    "9|qwen2.5-0.5b|qwen2_5-0.5b|qwen25-0.5b"
    "10|llama-3.2-1b|llama3.2-1b|llama_3.2_1b"
  )

  for kw_entry in "${FUZZY_KEYWORDS[@]}"; do
    IFS='|' read -r rank kw1 kw2 kw3 <<< "$kw_entry"
    [[ -n "${resolved[$rank]}" ]] && continue  # already found

    local found=""
    for kw in "$kw1" "$kw2" "$kw3"; do
      [[ -z "$kw" ]] && continue
      found=$(find ~ -type f -iname "*${kw}*.gguf" ! -path "*/backups/*" \
              -size +50M 2>/dev/null | head -1)
      [[ -n "$found" ]] && break
    done
    [[ -n "$found" ]] && resolved["$rank"]="$found"
  done

  # Step 3: any rank still unfilled — fill from scan_all_models (smallest first)
  # so we don't accidentally assign a 2GB model to rank-1 slot
  local remaining_models=()
  while IFS= read -r path; do
    local already_used=0
    for r in "${!resolved[@]}"; do
      [[ "${resolved[$r]}" == "$path" ]] && { already_used=1; break; }
    done
    [[ "$already_used" -eq 0 ]] && remaining_models+=("$path")
  done < <(scan_all_models | xargs -I{} sh -c 'echo "$(du -m "{}" | cut -f1) {}"' | sort -n | awk '{print $2}')

  local fill_idx=0
  for rank in $(seq 1 10); do
    [[ -n "${resolved[$rank]}" ]] && continue
    [[ "$fill_idx" -ge "${#remaining_models[@]}" ]] && break
    resolved["$rank"]="${remaining_models[$fill_idx]}"
    (( fill_idx++ ))
  done

  # Output filled slots in rank order
  for rank in $(seq 1 10); do
    [[ -n "${resolved[$rank]}" ]] && echo "$rank|${resolved[$rank]}"
  done
}

# ─── GET TOP-N PATHS ────────────────────────────────────────
get_top_n_paths() {
  local n="${1:-10}"
  local count=0
  while IFS='|' read -r rank path; do
    echo "$path"
    (( count++ ))
    (( count >= n )) && break
  done < <(resolve_top10_paths)
}

# ─── BUILD INTERACTIVE MODEL MENU ───────────────────────────
# BUG FIXED: All display output goes to stderr (>&2) so it is
# visible to the user. The function prints the final count to
# stdout, which is the only thing captured by $().
# Previously ALL output was captured → user saw blank screen.
build_model_menu() {
  mkdir -p "$(dirname "$LORNA_TMP/menu_models")"
  rm -f "$LORNA_TMP/menu_models"

  echo -e "  ${CYAN}${BOLD}Found Models:${NC}" >&2
  echo -e "  ${DIM}────────────────────────────────────────────────────────${NC}" >&2

  local idx=1
  while IFS= read -r path; do
    local name size_mb class
    name=$(basename "$path" .gguf)
    size_mb=$(du -m "$path" 2>/dev/null | cut -f1)
    class=$(model_load_class "$path" 2>/dev/null || echo "?")

    local cc=$GREEN
    [[ "$class" == "CAUTION" ]] && cc=$YELLOW
    [[ "$class" == "RISKY"   ]] && cc=$YELLOW
    [[ "$class" == "UNSAFE"  ]] && cc=$RED

    printf "  ${GOLD}%3d)${NC} %-40s ${DIM}%4dMB${NC}  ${cc}%s${NC}\n" \
      "$idx" "${name:0:40}" "$size_mb" "$class" >&2

    echo "$path" >> "$LORNA_TMP/menu_models"
    (( idx++ ))
  done < <(scan_all_models)

  # Only count goes to stdout — everything else already went to stderr
  echo $(( idx - 1 ))
}

# ─── SELECT MODEL FROM MENU BY NUMBER ───────────────────────
select_model() {
  local num="$1"
  [[ -f "$LORNA_TMP/menu_models" ]] || return 1
  sed -n "${num}p" "$LORNA_TMP/menu_models" 2>/dev/null
}

# ─── PRINT SPEED TABLE ──────────────────────────────────────
print_speed_table() {
  echo ""
  echo -e "  ${CYAN}${BOLD}TOP 10 — Generation Speed (Redmi 13C, measured)${NC}"
  echo -e "  ${DIM}──────────────────────────────────────────────────────${NC}"
  printf "  ${GOLD}%-3s  %-26s  %-10s  %-10s  %-6s${NC}\n" \
    "RNK" "MODEL" "GEN t/s" "PROMPT t/s" "MB"
  echo -e "  ${DIM}──────────────────────────────────────────────────────${NC}"

  local rows=(
    "1   Cerebras-111M          39-46      84-89      75"
    "2   NeoX-Tiny-125M         ~37        ~118       105"
    "3   node1_rwkv7            28-29      ~93        203"
    "4   Tool-270M              22-23      89-99      274"
    "5   SmolLM2-360M-Alt       18-22      52-83      369"
    "6   ERNIE-0.3B             19-20      60-66      230"
    "7   Qwen-Sentinel/0.5B     18-21      57-65      409"
    "8   SmolLM-360M            13-15      22-25      259"
    "9   Qwen2.5-0.5B-Instruct  14-15      ~21        470"
    "10  Llama-3.2-1B-Instruct  6.7        14-15      772"
  )
  for row in "${rows[@]}"; do
    printf "  %-3s  %-26s  %-10s  %-10s  %-6s\n" $row
  done
  echo ""
}
