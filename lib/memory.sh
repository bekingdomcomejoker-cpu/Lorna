#!/bin/bash
# ============================================================
# LORNA — lib/memory.sh  (v2 — all bugs fixed)
# RAM awareness, OOM prevention, model scheduling
# ============================================================

get_free_ram_mb() {
  awk '/^MemAvailable/ { printf "%d", $2/1024 }' /proc/meminfo 2>/dev/null || echo 0
}
get_free_swap_mb() {
  awk '/^SwapFree/ { printf "%d", $2/1024 }' /proc/meminfo 2>/dev/null || echo 0
}
get_total_ram_mb() {
  awk '/^MemTotal/ { printf "%d", $2/1024 }' /proc/meminfo 2>/dev/null || echo 0
}
get_swap_used_mb() {
  awk 'BEGIN{t=0;f=0}
       /^SwapTotal/{t=$2}
       /^SwapFree/ {f=$2}
       END{printf "%d",(t-f)/1024}' /proc/meminfo 2>/dev/null || echo 0
}

# ─── RAM NEEDED BY MODEL SIZE ───────────────────────────────
# ~1.5× file size + 200MB headroom for KV cache and OS overhead
required_ram_for_model() {
  local model_path="$1"
  local size_mb
  size_mb=$(du -m "$model_path" 2>/dev/null | cut -f1)
  echo $(( size_mb * 3 / 2 + 200 ))
}

# ─── SAFETY CLASSIFICATION ──────────────────────────────────
# Returns: SAFE / CAUTION / RISKY / UNSAFE
model_load_class() {
  local model_path="$1"
  local free_ram swap_used size_mb
  free_ram=$(get_free_ram_mb)
  swap_used=$(get_swap_used_mb)
  size_mb=$(du -m "$model_path" 2>/dev/null | cut -f1)

  if   (( size_mb <= 200 && free_ram >= 400 ));                      then echo "SAFE"
  elif (( size_mb <= 500 && free_ram >= 700 ));                      then echo "SAFE"
  elif (( size_mb <= 1200 && free_ram >= 1000 && swap_used < 1400)); then echo "CAUTION"
  elif (( free_ram >= 600 && swap_used < 1200 ));                    then echo "RISKY"
  else                                                                     echo "UNSAFE"
  fi
}

# ─── PRINT RAM STATUS ───────────────────────────────────────
print_ram_status() {
  local free total swap_used
  free=$(get_free_ram_mb)
  total=$(get_total_ram_mb)
  swap_used=$(get_swap_used_mb)
  local used=$(( total - free ))

  local color=$GREEN
  (( free < 600 )) && color=$YELLOW
  (( free < 300 )) && color=$RED

  echo -e "  RAM:  ${color}${free}MB free${NC} / ${total}MB total  (used: ${used}MB)"
  local sc=$DIM
  (( swap_used > 1400 )) && sc=$RED
  echo -e "  Swap: ${sc}${swap_used}MB used${NC}"
}

# ─── WAIT FOR MEMORY RECOVERY ───────────────────────────────
wait_for_memory_recovery() {
  local target_free="${1:-400}"
  local max_wait="${2:-8}"
  local waited=0
  while (( $(get_free_ram_mb) < target_free && waited < max_wait )); do
    sleep 1
    (( waited++ ))
  done
  sync 2>/dev/null
}

# ─── KILL ZOMBIE llama PROCESSES ────────────────────────────
cleanup_llama() {
  pkill -9 -f "llama-cli" 2>/dev/null || true
  sleep 1
  sync 2>/dev/null
}

# ─── PARALLEL SAFETY GATE ───────────────────────────────────
# Only models ≤300MB are safe to run simultaneously on 4GB RAM
is_parallel_safe() {
  local model_path="$1"
  local size_mb
  size_mb=$(du -m "$model_path" 2>/dev/null | cut -f1)
  (( size_mb <= 300 )) && return 0
  return 1
}
