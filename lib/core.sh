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
_LORNA_HAS_THREADS_BATCH=0
_LORNA_HAS_UBATCH=0
_LORNA_HAS_TOP_K=0
_LORNA_HAS_TOP_P=0
_LORNA_HAS_MIN_P=0
_LORNA_HAS_REPEAT_PENALTY=0
_LORNA_HAS_REPEAT_LAST_N=0
_LORNA_HAS_FREQUENCY_PENALTY=0
_LORNA_HAS_PRESENCE_PENALTY=0
_LORNA_HAS_TYPICAL=0
_LORNA_TYPICAL_FLAG=""
_LORNA_HAS_TFS=0
_LORNA_TFS_FLAG=""
_LORNA_HAS_DRY_MULTIPLIER=0
_LORNA_HAS_DRY_BASE=0
_LORNA_HAS_DRY_ALLOWED_LENGTH=0
_LORNA_HAS_DRY_PENALTY_LAST_N=0
_LORNA_HAS_DYNATEMP_RANGE=0
_LORNA_HAS_DYNATEMP_EXP=0
_LORNA_HAS_MIROSTAT=0
_LORNA_HAS_MIROSTAT_TAU=0
_LORNA_MIROSTAT_TAU_FLAG=""
_LORNA_HAS_MIROSTAT_ETA=0
_LORNA_MIROSTAT_ETA_FLAG=""
_LORNA_HAS_FLASH_ATTN=0

probe_binary_flags() {
  [[ "$_LORNA_FLAGS_TESTED" -eq 1 ]] && return
  [[ -z "$LLAMA_BIN" || ! -x "$LLAMA_BIN" ]] && { _LORNA_FLAGS_TESTED=1; return; }
  local help_text
  help_text=$("$LLAMA_BIN" --help 2>&1 || true)
  echo "$help_text" | grep -q "no-warmup"      && _LORNA_HAS_NO_WARMUP=1
  echo "$help_text" | grep -q "cache-type-k"   && _LORNA_HAS_CACHE_TYPE=1
  echo "$help_text" | grep -q "threads-batch"  && _LORNA_HAS_THREADS_BATCH=1
  echo "$help_text" | grep -q "ubatch-size"    && _LORNA_HAS_UBATCH=1
  echo "$help_text" | grep -q "top-k"          && _LORNA_HAS_TOP_K=1
  echo "$help_text" | grep -q "top-p"          && _LORNA_HAS_TOP_P=1
  echo "$help_text" | grep -q "min-p"          && _LORNA_HAS_MIN_P=1
  echo "$help_text" | grep -q "repeat-penalty" && _LORNA_HAS_REPEAT_PENALTY=1
  echo "$help_text" | grep -q "repeat-last-n"  && _LORNA_HAS_REPEAT_LAST_N=1
  echo "$help_text" | grep -q "frequency-penalty" && _LORNA_HAS_FREQUENCY_PENALTY=1
  echo "$help_text" | grep -q "presence-penalty" && _LORNA_HAS_PRESENCE_PENALTY=1
  if echo "$help_text" | grep -q -- "--typical-p"; then
    _LORNA_HAS_TYPICAL=1; _LORNA_TYPICAL_FLAG="--typical-p"
  elif echo "$help_text" | grep -q -- "--typical"; then
    _LORNA_HAS_TYPICAL=1; _LORNA_TYPICAL_FLAG="--typical"
  fi
  if echo "$help_text" | grep -q -- "--tfs-z"; then
    _LORNA_HAS_TFS=1; _LORNA_TFS_FLAG="--tfs-z"
  elif echo "$help_text" | grep -q -- "--tfs"; then
    _LORNA_HAS_TFS=1; _LORNA_TFS_FLAG="--tfs"
  fi
  echo "$help_text" | grep -q "dry-multiplier" && _LORNA_HAS_DRY_MULTIPLIER=1
  echo "$help_text" | grep -q "dry-base" && _LORNA_HAS_DRY_BASE=1
  echo "$help_text" | grep -q "dry-allowed-length" && _LORNA_HAS_DRY_ALLOWED_LENGTH=1
  echo "$help_text" | grep -q "dry-penalty-last-n" && _LORNA_HAS_DRY_PENALTY_LAST_N=1
  echo "$help_text" | grep -q "dynatemp-range" && _LORNA_HAS_DYNATEMP_RANGE=1
  echo "$help_text" | grep -q "dynatemp-exp" && _LORNA_HAS_DYNATEMP_EXP=1
  echo "$help_text" | grep -q "mirostat" && _LORNA_HAS_MIROSTAT=1
  if echo "$help_text" | grep -q -- "--mirostat-ent"; then
    _LORNA_HAS_MIROSTAT_TAU=1; _LORNA_MIROSTAT_TAU_FLAG="--mirostat-ent"
  elif echo "$help_text" | grep -q -- "--mirostat-tau"; then
    _LORNA_HAS_MIROSTAT_TAU=1; _LORNA_MIROSTAT_TAU_FLAG="--mirostat-tau"
  fi
  if echo "$help_text" | grep -q -- "--mirostat-lr"; then
    _LORNA_HAS_MIROSTAT_ETA=1; _LORNA_MIROSTAT_ETA_FLAG="--mirostat-lr"
  elif echo "$help_text" | grep -q -- "--mirostat-eta"; then
    _LORNA_HAS_MIROSTAT_ETA=1; _LORNA_MIROSTAT_ETA_FLAG="--mirostat-eta"
  fi
  echo "$help_text" | grep -q "flash-attn"     && _LORNA_HAS_FLASH_ATTN=1
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

# Lorna2 stores validated per-model presets outside the repository so device
# optimization state survives updates without becoming tracked source data.
get_model_runtime_config() {
  local model_path="$1"
  local ctx batch threads temp
  read -r ctx batch threads temp <<< "$(get_model_tier "$model_path")"
  local agent_manager="${LORNA_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}/agents/benchmark_manager.py"
  local preset_line=""
  if command -v python3 >/dev/null 2>&1 && [[ -f "$agent_manager" ]]; then
    preset_line=$(python3 "$agent_manager" preset-line "$model_path" 2>/dev/null || true)
  fi
  if [[ "$preset_line" =~ ^[0-9]+[[:space:]][0-9]+[[:space:]][0-9]+[[:space:]][0-9.]+ ]]; then
    echo "$preset_line"
  else
    echo "$ctx $batch $threads $temp $threads $batch q4_0 q4_0 auto 40 0.95 0.05 1.05 64 0.0 0.0 1.0 1.0 0.0 1.75 2 64 0.0 1.0 0 5.0 0.1"
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

  local ctx batch threads temp_default threads_batch ubatch cache_k cache_v flash_attn top_k top_p min_p repeat_penalty repeat_last_n frequency_penalty presence_penalty typical_p tfs_z dry_multiplier dry_base dry_allowed_length dry_penalty_last_n dynatemp_range dynatemp_exp mirostat mirostat_tau mirostat_eta
  read -r ctx batch threads temp_default threads_batch ubatch cache_k cache_v flash_attn top_k top_p min_p repeat_penalty repeat_last_n frequency_penalty presence_penalty typical_p tfs_z dry_multiplier dry_base dry_allowed_length dry_penalty_last_n dynatemp_range dynatemp_exp mirostat mirostat_tau mirostat_eta <<< "$(get_model_runtime_config "$model")"
  local temp="${temp_override:-$temp_default}"

  probe_binary_flags

  local extra_flags=()
  [[ "$_LORNA_HAS_NO_WARMUP"      -eq 1 ]] && extra_flags+=(--no-warmup)
  [[ "$_LORNA_HAS_CACHE_TYPE"     -eq 1 ]] && extra_flags+=(--cache-type-k "$cache_k" --cache-type-v "$cache_v")
  [[ "$_LORNA_HAS_THREADS_BATCH"  -eq 1 ]] && extra_flags+=(--threads-batch "$threads_batch")
  [[ "$_LORNA_HAS_UBATCH"         -eq 1 ]] && extra_flags+=(--ubatch-size "$ubatch")
  [[ "$_LORNA_HAS_TOP_K"          -eq 1 ]] && extra_flags+=(--top-k "$top_k")
  [[ "$_LORNA_HAS_TOP_P"          -eq 1 ]] && extra_flags+=(--top-p "$top_p")
  [[ "$_LORNA_HAS_MIN_P"          -eq 1 ]] && extra_flags+=(--min-p "$min_p")
  [[ "$_LORNA_HAS_REPEAT_PENALTY" -eq 1 ]] && extra_flags+=(--repeat-penalty "$repeat_penalty")
  [[ "$_LORNA_HAS_REPEAT_LAST_N" -eq 1 ]] && extra_flags+=(--repeat-last-n "$repeat_last_n")
  [[ "$_LORNA_HAS_FREQUENCY_PENALTY" -eq 1 ]] && extra_flags+=(--frequency-penalty "$frequency_penalty")
  [[ "$_LORNA_HAS_PRESENCE_PENALTY" -eq 1 ]] && extra_flags+=(--presence-penalty "$presence_penalty")
  [[ "$_LORNA_HAS_TYPICAL" -eq 1 ]] && extra_flags+=("$_LORNA_TYPICAL_FLAG" "$typical_p")
  [[ "$_LORNA_HAS_TFS" -eq 1 ]] && extra_flags+=("$_LORNA_TFS_FLAG" "$tfs_z")
  [[ "$_LORNA_HAS_DRY_MULTIPLIER" -eq 1 ]] && extra_flags+=(--dry-multiplier "$dry_multiplier")
  [[ "$_LORNA_HAS_DRY_BASE" -eq 1 ]] && extra_flags+=(--dry-base "$dry_base")
  [[ "$_LORNA_HAS_DRY_ALLOWED_LENGTH" -eq 1 ]] && extra_flags+=(--dry-allowed-length "$dry_allowed_length")
  [[ "$_LORNA_HAS_DRY_PENALTY_LAST_N" -eq 1 ]] && extra_flags+=(--dry-penalty-last-n "$dry_penalty_last_n")
  [[ "$_LORNA_HAS_DYNATEMP_RANGE" -eq 1 ]] && extra_flags+=(--dynatemp-range "$dynatemp_range")
  [[ "$_LORNA_HAS_DYNATEMP_EXP" -eq 1 ]] && extra_flags+=(--dynatemp-exp "$dynatemp_exp")
  [[ "$_LORNA_HAS_MIROSTAT" -eq 1 ]] && extra_flags+=(--mirostat "$mirostat")
  [[ "$_LORNA_HAS_MIROSTAT_TAU" -eq 1 ]] && extra_flags+=("$_LORNA_MIROSTAT_TAU_FLAG" "$mirostat_tau")
  [[ "$_LORNA_HAS_MIROSTAT_ETA" -eq 1 ]] && extra_flags+=("$_LORNA_MIROSTAT_ETA_FLAG" "$mirostat_eta")
  [[ "$_LORNA_HAS_FLASH_ATTN"     -eq 1 ]] && extra_flags+=(--flash-attn "$flash_attn")

  [[ -n "$LORNA_VERBOSE" ]] && \
    echo -e "${DIM}  → $(get_model_name "$model") ctx=$ctx b=$batch/$ubatch t=$threads/$threads_batch temp=$temp n=$n_tokens${NC}" >&2

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
  local ctx batch threads temp_default threads_batch ubatch cache_k cache_v flash_attn top_k top_p min_p repeat_penalty repeat_last_n frequency_penalty presence_penalty typical_p tfs_z dry_multiplier dry_base dry_allowed_length dry_penalty_last_n dynatemp_range dynatemp_exp mirostat mirostat_tau mirostat_eta
  read -r ctx batch threads temp_default threads_batch ubatch cache_k cache_v flash_attn top_k top_p min_p repeat_penalty repeat_last_n frequency_penalty presence_penalty typical_p tfs_z dry_multiplier dry_base dry_allowed_length dry_penalty_last_n dynatemp_range dynatemp_exp mirostat mirostat_tau mirostat_eta <<< "$(get_model_runtime_config "$model")"
  local temp="${temp_override:-$temp_default}"

  probe_binary_flags
  local extra_flags=()
  [[ "$_LORNA_HAS_CACHE_TYPE"     -eq 1 ]] && extra_flags+=(--cache-type-k "$cache_k" --cache-type-v "$cache_v")
  [[ "$_LORNA_HAS_THREADS_BATCH"  -eq 1 ]] && extra_flags+=(--threads-batch "$threads_batch")
  [[ "$_LORNA_HAS_UBATCH"         -eq 1 ]] && extra_flags+=(--ubatch-size "$ubatch")
  [[ "$_LORNA_HAS_TOP_K"          -eq 1 ]] && extra_flags+=(--top-k "$top_k")
  [[ "$_LORNA_HAS_TOP_P"          -eq 1 ]] && extra_flags+=(--top-p "$top_p")
  [[ "$_LORNA_HAS_MIN_P"          -eq 1 ]] && extra_flags+=(--min-p "$min_p")
  [[ "$_LORNA_HAS_REPEAT_PENALTY" -eq 1 ]] && extra_flags+=(--repeat-penalty "$repeat_penalty")
  [[ "$_LORNA_HAS_REPEAT_LAST_N" -eq 1 ]] && extra_flags+=(--repeat-last-n "$repeat_last_n")
  [[ "$_LORNA_HAS_FREQUENCY_PENALTY" -eq 1 ]] && extra_flags+=(--frequency-penalty "$frequency_penalty")
  [[ "$_LORNA_HAS_PRESENCE_PENALTY" -eq 1 ]] && extra_flags+=(--presence-penalty "$presence_penalty")
  [[ "$_LORNA_HAS_TYPICAL" -eq 1 ]] && extra_flags+=("$_LORNA_TYPICAL_FLAG" "$typical_p")
  [[ "$_LORNA_HAS_TFS" -eq 1 ]] && extra_flags+=("$_LORNA_TFS_FLAG" "$tfs_z")
  [[ "$_LORNA_HAS_DRY_MULTIPLIER" -eq 1 ]] && extra_flags+=(--dry-multiplier "$dry_multiplier")
  [[ "$_LORNA_HAS_DRY_BASE" -eq 1 ]] && extra_flags+=(--dry-base "$dry_base")
  [[ "$_LORNA_HAS_DRY_ALLOWED_LENGTH" -eq 1 ]] && extra_flags+=(--dry-allowed-length "$dry_allowed_length")
  [[ "$_LORNA_HAS_DRY_PENALTY_LAST_N" -eq 1 ]] && extra_flags+=(--dry-penalty-last-n "$dry_penalty_last_n")
  [[ "$_LORNA_HAS_DYNATEMP_RANGE" -eq 1 ]] && extra_flags+=(--dynatemp-range "$dynatemp_range")
  [[ "$_LORNA_HAS_DYNATEMP_EXP" -eq 1 ]] && extra_flags+=(--dynatemp-exp "$dynatemp_exp")
  [[ "$_LORNA_HAS_MIROSTAT" -eq 1 ]] && extra_flags+=(--mirostat "$mirostat")
  [[ "$_LORNA_HAS_MIROSTAT_TAU" -eq 1 ]] && extra_flags+=("$_LORNA_MIROSTAT_TAU_FLAG" "$mirostat_tau")
  [[ "$_LORNA_HAS_MIROSTAT_ETA" -eq 1 ]] && extra_flags+=("$_LORNA_MIROSTAT_ETA_FLAG" "$mirostat_eta")
  [[ "$_LORNA_HAS_FLASH_ATTN"     -eq 1 ]] && extra_flags+=(--flash-attn "$flash_attn")

  echo -e "${DIM}  ctx=$ctx  batch=$batch/$ubatch  threads=$threads/$threads_batch  temp=$temp${NC}"
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
