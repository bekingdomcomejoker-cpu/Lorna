#!/bin/bash
# ============================================================
# LORNA — tools/health.sh  (v2 — all bugs fixed)
# System health diagnostics for Termux LLM environment
#
# BUG FIXED: pgrep -a not available on all Termux builds.
# Use ps + grep as fallback.
# ============================================================

LORNA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$LORNA_DIR/lib/core.sh"
source "$LORNA_DIR/lib/memory.sh"
source "$LORNA_DIR/lib/registry.sh"

# ─── PORTABLE PROCESS LIST ──────────────────────────────────
# pgrep -a (show full cmdline) not available in all Termux builds
list_llama_procs() {
  # Try pgrep -a first; if it fails, fall back to ps
  if pgrep -a "llama-cli" >/dev/null 2>&1; then
    pgrep -a "llama-cli" 2>/dev/null
  else
    ps aux 2>/dev/null | grep "llama-cli" | grep -v grep || true
  fi
}

run_health() {
  lorna_banner
  echo -e "  ${BOLD}SYSTEM HEALTH CHECK${NC}"
  echo ""

  # ─── BINARY INVENTORY ─────────────────────────────────
  echo -e "  ${BOLD}llama-cli Binaries on Device:${NC}"

  local found_any=0
  local candidate_paths=(
    "/data/data/com.termux/files/home/llama.cpp/build/bin/llama-cli"
    "/data/data/com.termux/files/home/federation/llama.cpp/build/bin/llama-cli"
    "/data/data/com.termux/files/home/bin/llama-cli"
  )
  # Add PATH binary if different
  local path_bin
  path_bin=$(which llama-cli 2>/dev/null)
  [[ -n "$path_bin" ]] && candidate_paths+=("$path_bin")

  for bin in "${candidate_paths[@]}"; do
    local real
    real=$(readlink -f "$bin" 2>/dev/null)
    if [[ -x "$real" ]]; then
      local size
      size=$(stat -c%s "$real" 2>/dev/null || echo "?")
      local label="${GREEN}  ✓${NC}"
      (( size < 10000000 )) && label="${YELLOW}  ⚠${NC}"
      local symlink_note=""
      [[ "$bin" != "$real" ]] && symlink_note=" ${DIM}→ $real${NC}"
      printf "%b %-58s  ${DIM}%s bytes${NC}%b\n" "$label" "$bin" "$size" "$symlink_note"
      found_any=1
    else
      echo -e "  ${DIM}  · $bin (not found)${NC}"
    fi
  done

  echo ""
  echo -e "  ${BOLD}Active binary (LORNA will use):${NC}"
  if [[ -n "$LLAMA_BIN" && -x "$LLAMA_BIN" ]]; then
    local sz
    sz=$(stat -c%s "$LLAMA_BIN" 2>/dev/null || echo "?")
    ok "$LLAMA_BIN"
    info "Size: ${sz} bytes"
    if (( sz < 10000000 )); then
      warn "This binary is very small (<10MB) — may be an old federation build."
      warn "Recommend rebuilding: cd ~/llama.cpp && cmake -B build && cmake --build build -j4"
    else
      ok "Size looks correct (full build)"
    fi
  else
    err "No valid llama-cli binary detected!"
    warn "Run: bash $LORNA_DIR/install.sh"
  fi

  # ─── BINARY COLLISION DETECTOR ────────────────────────
  echo ""
  echo -e "  ${BOLD}Binary Collision Check:${NC}"
  local active_path_bin
  active_path_bin=$(which llama-cli 2>/dev/null)
  if [[ -n "$active_path_bin" && -n "$LLAMA_BIN" ]]; then
    local real_path_bin
    real_path_bin=$(readlink -f "$active_path_bin")
    if [[ "$real_path_bin" != "$LLAMA_BIN" ]]; then
      warn "PATH binary resolves to: $real_path_bin"
      warn "LORNA uses:              $LLAMA_BIN"
      warn "COLLISION — scripts using plain 'llama-cli' will use the wrong binary!"
      echo ""
      echo -e "  ${DIM}Fix by adding to ~/.bashrc:${NC}"
      echo -e "  ${CYAN}  export PATH=\"/data/data/com.termux/files/usr/bin:\$HOME/llama.cpp/build/bin:\$HOME/.local/bin\"${NC}"
    else
      ok "No collision — PATH binary matches LORNA binary"
    fi
  fi

  # ─── MEMORY ───────────────────────────────────────────
  echo ""
  echo -e "  ${BOLD}Memory Status:${NC}"
  print_ram_status

  local free_ram swap_used
  free_ram=$(get_free_ram_mb)
  swap_used=$(get_swap_used_mb)
  echo ""

  if   (( free_ram >= 1000 && swap_used < 1000 )); then ok "RAM state: HEALTHY — safe for heavy models"
  elif (( free_ram >= 600  && swap_used < 1400 )); then warn "RAM state: MODERATE — use ≤1B models"
  elif (( free_ram >= 400  ));                     then warn "RAM state: TIGHT — use ≤500MB models only"
  else                                                  err "RAM state: CRITICAL — restart Termux before loading any model"
  fi

  # ─── MODEL INVENTORY ──────────────────────────────────
  echo ""
  echo -e "  ${BOLD}Model Inventory:${NC}"
  local count=0 total_size=0

  while IFS= read -r path; do
    local name size_mb class
    name=$(basename "$path" .gguf)
    size_mb=$(du -m "$path" 2>/dev/null | cut -f1)
    class=$(model_load_class "$path")
    local cc=$GREEN
    [[ "$class" == "CAUTION" ]] && cc=$YELLOW
    [[ "$class" == "RISKY"   ]] && cc=$YELLOW
    [[ "$class" == "UNSAFE"  ]] && cc=$RED
    printf "  ${DIM}·${NC} %-44s ${DIM}%4dMB${NC}  ${cc}%-8s${NC}\n" \
      "${name:0:44}" "$size_mb" "$class"
    (( count++ ))
    (( total_size += size_mb ))
  done < <(scan_all_models)

  if (( count == 0 )); then
    warn "No models found. Expected locations: ~/federation/models, ~/models"
  else
    echo ""
    info "$count models found · ${total_size}MB total on disk"
  fi

  # ─── TOP-10 RESOLUTION ────────────────────────────────
  echo ""
  echo -e "  ${BOLD}Top-10 Speed Model Resolution:${NC}"
  local resolved=0
  while IFS='|' read -r rank path; do
    ok "#${rank}: $(basename "$path" .gguf)"
    (( resolved++ ))
  done < <(resolve_top10_paths)

  local missing=$(( 10 - resolved ))
  if (( resolved == 0 )); then
    warn "No top-10 models resolved — chain/race will use all-models fallback"
  elif (( missing > 0 )); then
    warn "$missing top-10 slot(s) not matched by filename — fallback models used"
  fi

  # ─── PATH DUPLICATES ──────────────────────────────────
  echo ""
  echo -e "  ${BOLD}PATH Duplicate Check:${NC}"
  local dup_count
  dup_count=$(echo "$PATH" | tr ':' '\n' | sort | uniq -d | wc -l)
  if (( dup_count > 0 )); then
    warn "Duplicate PATH entries detected ($dup_count): can cause binary collision"
    echo "$PATH" | tr ':' '\n' | sort | uniq -d | sed 's/^/    /'
  else
    ok "No PATH duplicates"
  fi

  # ─── ZOMBIE PROCESSES ─────────────────────────────────
  echo ""
  echo -e "  ${BOLD}Active llama-cli Processes:${NC}"
  local procs
  procs=$(list_llama_procs)

  if [[ -n "$procs" ]]; then
    warn "Found running llama-cli processes:"
    echo "$procs" | sed 's/^/    /'
    echo ""
    read -rp "  Kill all llama-cli processes? [y/N]: " kill_confirm
    if [[ "${kill_confirm,,}" == "y" ]]; then
      cleanup_llama
      ok "Killed."
    fi
  else
    ok "No running llama-cli processes"
  fi

  # ─── QUICK BINARY SMOKE TEST ──────────────────────────
  echo ""
  echo -e "  ${BOLD}Binary Smoke Test:${NC}"
  if [[ -n "$LLAMA_BIN" && -x "$LLAMA_BIN" ]]; then
    local version_out
    version_out=$("$LLAMA_BIN" --version 2>&1 | head -1 || \
                  "$LLAMA_BIN" --help 2>&1 | head -2 || echo "unknown")
    info "Binary response: $version_out"
    ok "Binary is executable"

    # Check which flags are supported
    probe_binary_flags
    local flag_status=""
    [[ "$_LORNA_HAS_NO_WARMUP"  -eq 1 ]] && flag_status+=" --no-warmup"
    [[ "$_LORNA_HAS_CACHE_TYPE" -eq 1 ]] && flag_status+=" --cache-type-k"
    if [[ -n "$flag_status" ]]; then
      ok "Supported optional flags:$flag_status"
    else
      warn "Binary may be older build — optional performance flags not available"
    fi
  else
    err "Binary not executable"
  fi

  echo ""
  echo -e "${GREEN}${BOLD}  ✓ Health check complete.${NC}"
  echo ""
  info "Tip: Run 'lorna bench safe' to measure real t/s for all your models"
}

run_health "$@"
