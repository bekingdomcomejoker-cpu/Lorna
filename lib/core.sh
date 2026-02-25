#!/bin/bash
# ============================================================
# LORNA — lib/core.sh  (v2 — all bugs fixed)
# Shared functions: binary detection, tier config, model runner
# ============================================================

# ─── COLORS ─────────────────────────────────────────────────
RED='\033[0;31m'   YELLOW='\033[1;33m'  GREEN='\033[0;32m'
CYAN='\033[0;36m'  BOLD='\033[1m'       DIM='\033[2m'
GOLD='\033[0;33m'  NC='\033[0m'

# ─── TMPDIR SAFETY ──────────────────────────────────────────
LORNA_TMP="${TMPDIR:-/data/data/com.termux/files/usr/tmp}/lorna"
# Explicitly create the directory whenever core.sh is sourced
mkdir -p "$LORNA_TMP" 2>/dev/null || true

# ─── LOG DIR (cached — not recreated on every call) ──────────
LORNA_LOG_DIR="$HOME/lorna_logs"
_LORNA_LOG_DIR_READY=0
_ensure_log_dir() {
  if [[ "$_LORNA_LOG_DIR_READY" -eq 0 ]]; then
    mkdir -p "$LORNA_LOG_DIR"
    _LORNA_LOG_DIR_READY=1
  fi
}
LORNA_LOG="$LORNA_LOG_DIR/session_$(date +%Y%m%d_%H%M%S).log"
log() { _ensure_log_dir; echo "[$(date +%H:%M:%S)] $*" >> "$LORNA_LOG"; }

# ─── BANNER ─────────────────────────────────────────────────
lorna_banner() {
  clear
  echo -e "${CYAN}${BOLD}"
  echo "  ██╗      ██████╗ ██████╗ ███╗   ██╗ █████╗ "
  echo "  ██║     ██╔═══██╗██╔══██╗████╗  ██║██╔══██╗"
  echo "  ██║     ██║   ██║██████╔╝██╔██╗ ██║███████║"
  echo "  ██║     ██║   ██║██╔══██╗██║╚██╗██║██╔══██║"
  echo "  ███████╗╚██████╔╝██║  ██║██║ ╚████║██║  ██║"
  echo "  ╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝"
  echo -e "${NC}${DIM}  Local Offline Reasoning Node Architecture${NC}"
  echo -e "${DIM}  Redmi 13C · Helio G85 · 4GB RAM · Termux · llama.cpp${NC}"
  echo ""
}

# ─── BINARY DETECTION ───────────────────────────────────────
# Picks the LARGEST (most complete) llama-cli binary found.
# The 68MB full build beats the 4.5MB federation symlink.
detect_llama_binary() {
  local candidates=(
    "/home/ubuntu/llama-cli-mock.sh"
    "/data/data/com.termux/files/home/SOVEREIGN_HOME/termux-forge/llama.cpp/build/bin/llama-cli"
    "/data/data/com.termux/files/home/llama.cpp/build/bin/llama-cli"
    "$HOME/llama.cpp/build/bin/llama-cli"
    "$HOME/federation/llama.cpp/build/bin/llama-cli"
  )
  local path_bin
  path_bin=$(which llama-cli 2>/dev/null)
  [[ -n "$path_bin" ]] && candidates+=("$path_bin")

  local best_path="" best_size=0
  for candidate in "${candidates[@]}"; do
    local real
    real=$(readlink -f "$candidate" 2>/dev/null)
    [[ -x "$real" ]] || continue
    local size
    size=$(stat -c%s "$real" 2>/dev/null || echo 0)
    if (( size > best_size )); then
      best_size=$size
      best_path="$real"
    fi
  done
  echo "$best_path"
}

LLAMA_BIN="$(detect_llama_binary)"
export LLAMA_BIN

# ─── BINARY CAPABILITY FLAGS ────────────────────────────────
# Probed once — avoids passing unsupported flags that crash older builds
_LORNA_FLAGS_TESTED=0
_LORNA_HAS_NO_WARMUP=0
_LORNA_HAS_CACHE_TYPE=0

probe_binary_flags() {
  [[ "$_LORNA_FLAGS_TESTED" -eq 1 ]] && return
  [[ -z "$LLAMA_BIN" || ! -x "$LLAMA_BIN" ]] && { _LORNA_FLAGS_TESTED=1; return; }
  local help_text
  help_text=$("$LLAMA_BIN" --help 2>&1 || true)
  echo "$help_text" | grep -q "no-warmup"    && _LORNA_HAS_NO_WARMUP=1
  echo "$help_text" | grep -q "cache-type-k" && _LORNA_HAS_CACHE_TYPE=1
  _LORNA_FLAGS_TESTED=1
}

# ─── AUTO-TIER CONFIGURATION ────────────────────────────────
# BUG FIXED: All strings use single spaces only.
# Old bug: "768 96  4 0.6" → read parsed threads="" (empty) → -t "" → crash
get_model_tier() {
  local model_path="$1"
  local size_mb
  size_mb=$(du -m "$model_path" 2>/dev/null | cut -f1)
  size_mb=${size_mb:-0}

  if   (( size_mb <= 150  )); then echo "512 256 4 0.7"
  elif (( size_mb <= 350  )); then echo "768 128 4 0.7"
  elif (( size_mb <= 800  )); then echo "768 96 4 0.6"
  elif (( size_mb <= 1200 )); then echo "1024 64 4 0.5"
  elif (( size_mb <= 1800 )); then echo "768 48 3 0.4"
  else                              echo "512 32 2 0.3"
  fi
}

get_model_size_mb() { du -m "$1" 2>/dev/null | cut -f1; }
get_model_name()    { basename "$1" .gguf; }

# ─── SINGLE MODEL RUNNER (FILE / BATCH MODE) ─────────────────
# BUG FIXED: Added < /dev/null for models ≤1000MB to prevent
# interactive hang (">>> " waiting forever) documented across
# all PDF logs. Skipped for large models where OOM spike is risky.
#
# run_model <model> <prompt_file> <output_file> [n_tokens] [temp]
run_model() {
  local model="$1"
  local prompt_file="$2"
  local output_file="$3"
  local n_tokens="${4:-128}"
  local temp_override="$5"

  read -r ctx batch threads temp_default <<< "$(get_model_tier "$model")"
  local temp="${temp_override:-$temp_default}"

  probe_binary_flags

  local extra_flags=()
  [[ "$_LORNA_HAS_NO_WARMUP"  -eq 1 ]] && extra_flags+=(--no-warmup)
  [[ "$_LORNA_HAS_CACHE_TYPE" -eq 1 ]] && extra_flags+=(--cache-type-k q4_0 --cache-type-v q4_0)

  [[ -n "$LORNA_VERBOSE" ]] && \
    echo -e "${DIM}  → $(get_model_name "$model") ctx=$ctx b=$batch t=$threads temp=$temp n=$n_tokens${NC}" >&2

  local size_mb
  size_mb=$(get_model_size_mb "$model")

  # Close stdin for small/medium — prevents interactive hang
  if (( size_mb <= 1000 )); then
    "$LLAMA_BIN" \
      -m  "$model"       \
      -f  "$prompt_file" \
      -n  "$n_tokens"    \
      -c  "$ctx"         \
      -t  "$threads"     \
      -b  "$batch"       \
      --temp "$temp"     \
      --no-display-prompt \
      "${extra_flags[@]}" \
      2>/dev/null > "$output_file" < /dev/null
  else
    # Large models: leave stdin alone to avoid OOM spike on Android
    "$LLAMA_BIN" \
      -m  "$model"       \
      -f  "$prompt_file" \
      -n  "$n_tokens"    \
      -c  "$ctx"         \
      -t  "$threads"     \
      -b  "$batch"       \
      --temp "$temp"     \
      --no-display-prompt \
      "${extra_flags[@]}" \
      2>/dev/null > "$output_file"
  fi
}

# ─── INTERACTIVE MODEL RUNNER ────────────────────────────────
# For solo mode only — real multi-turn conversation
run_model_interactive() {
  local model="$1"
  local temp_override="$2"
  read -r ctx batch threads temp_default <<< "$(get_model_tier "$model")"
  local temp="${temp_override:-$temp_default}"

  probe_binary_flags
  local extra_flags=()
  [[ "$_LORNA_HAS_CACHE_TYPE" -eq 1 ]] && extra_flags+=(--cache-type-k q4_0 --cache-type-v q4_0)

  echo -e "${DIM}  ctx=$ctx  batch=$batch  threads=$threads  temp=$temp${NC}"
  echo -e "${DIM}  Type /exit or Ctrl+C to quit${NC}"
  echo ""

  "$LLAMA_BIN" \
    -m "$model"    \
    -c "$ctx"      \
    -t "$threads"  \
    -b "$batch"    \
    --temp "$temp" \
    "${extra_flags[@]}" \
    --conversation
}

# ─── COMPRESS CONTEXT ────────────────────────────────────────
compress_output() {
  local text="$1"
  local max_lines="${2:-40}"
  echo "$text" | head -n "$max_lines"
}

# ─── PRINT HELPERS ───────────────────────────────────────────
ok()   { echo -e "${GREEN}  ✓${NC} $*"; }
info() { echo -e "${CYAN}  ·${NC} $*"; }
warn() { echo -e "${YELLOW}  ⚠${NC} $*"; }
err()  { echo -e "${RED}  ✗${NC} $*"; }

node_header() {
  local num="$1" label="$2"
  echo ""
  echo -e "${GOLD}${BOLD}  ┌─ NODE ${num} ─ ${label}${NC}"
  echo -e "${GOLD}  │${NC}"
}
node_footer() {
  echo -e "${DIM}  └──────────────────────────────────────────────────${NC}"
}
