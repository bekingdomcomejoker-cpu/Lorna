#!/bin/bash
# ============================================================
# LORNA — pipelines/solo.sh  (v2 — all bugs fixed)
# Run a single model interactively with memory safety
# ============================================================

LORNA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$LORNA_DIR/lib/core.sh"
source "$LORNA_DIR/lib/memory.sh"
source "$LORNA_DIR/lib/registry.sh"

run_solo() {
  lorna_banner
  echo -e "  ${BOLD}MODE: SOLO — Single Model Interactive${NC}"
  echo ""
  print_ram_status
  echo ""

  # BUG FIXED: build_model_menu writes display to stderr,
  # returns only the count to stdout — menu is now actually visible
  local count
  count=$(build_model_menu)
  echo "" >&2

  if [[ "$count" -eq 0 ]]; then
    err "No models found. Check ~/federation/models or ~/models"
    return 1
  fi

  local selection="${1:-}"
  if [[ -z "$selection" ]]; then
    read -rp "  Select model [1-$count]: " selection
  fi

  if ! [[ "$selection" =~ ^[0-9]+$ ]] || (( selection < 1 || selection > count )); then
    err "Invalid selection: $selection"
    return 1
  fi

  local model
  model=$(select_model "$selection")

  if [[ -z "$model" || ! -f "$model" ]]; then
    err "Model path not found for selection $selection"
    return 1
  fi

  local name size_mb class
  name=$(basename "$model" .gguf)
  size_mb=$(du -m "$model" | cut -f1)
  class=$(model_load_class "$model")

  echo ""
  info "Selected: ${BOLD}$name${NC} (${size_mb}MB)"

  case "$class" in
    UNSAFE)
      err "Insufficient RAM to load this model safely."
      warn "Try: pkill -9 llama-cli && sleep 3, then re-run"
      return 1 ;;
    RISKY)
      warn "Low RAM. Model may be OOM-killed by Android. Continue? [y/N]"
      read -rp "  > " confirm
      [[ "${confirm,,}" != "y" ]] && return 0 ;;
    CAUTION)
      warn "Moderate RAM pressure — tier-appropriate context will be used." ;;
  esac

  # BUG FIXED: warn before killing, don't silently murder other sessions
  local procs
  procs=$(pgrep -f "llama-cli" 2>/dev/null)
  if [[ -n "$procs" ]]; then
    warn "Another llama-cli is running. Kill it? [y/N]"
    read -rp "  > " kill_confirm
    [[ "${kill_confirm,,}" == "y" ]] && cleanup_llama && ok "Cleared."
  fi

  echo ""
  ok "Loading $name..."
  log "SOLO START: $name (${size_mb}MB) | RAM: $(get_free_ram_mb)MB"
  echo ""
  echo -e "${DIM}  ──────────────────────────────────────────────────────${NC}"
  run_model_interactive "$model"
  echo -e "${DIM}  ──────────────────────────────────────────────────────${NC}"
  echo ""
  ok "Session ended."
  log "SOLO END: $name"
}

run_solo "$@"
