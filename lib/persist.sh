#!/bin/bash
# LORNA v3 — lib/persist.sh
# Persistent memory system for session continuity

MEMORY_DIR="$HOME/.lorna_memory"
mkdir -p "$MEMORY_DIR"

save_context() {
  local session_id="$1"
  local context="$2"
  echo "$context" > "$MEMORY_DIR/${session_id}.ctx"
}

load_context() {
  local session_id="$1"
  [[ -f "$MEMORY_DIR/${session_id}.ctx" ]] && cat "$MEMORY_DIR/${session_id}.ctx"
}

list_sessions() {
  ls -1 "$MEMORY_DIR"/*.ctx 2>/dev/null | while read f; do
    local sid=$(basename "$f" .ctx)
    local size=$(wc -c < "$f")
    local date=$(stat -c%y "$f" 2>/dev/null | cut -d' ' -f1)
    printf "  ${GOLD}%-20s${NC} ${DIM}%s  %s bytes${NC}\n" "$sid" "$date" "$size"
  done
}

clear_session() {
  local session_id="$1"
  rm -f "$MEMORY_DIR/${session_id}.ctx"
}
