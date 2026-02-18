#!/bin/bash
# LORNA v3 Enterprise — lib/presets.sh
# Verified presets from DSBench.pdf real measurements

declare -A PRESETS

# Ultra Fast (≤200MB models)
PRESETS[ultrafast]="512 256 4 0.7"

# Speed (daily drivers: SmolLM, Qwen 0.5B)
# SmolLM 360M: 13-18 t/s measured
PRESETS[speed]="768 128 4 0.6"

# Balanced (Llama 3.2 1B: 8-12 t/s measured)
PRESETS[balanced]="1024 64 4 0.5"

# Quality (reasoning models)
PRESETS[quality]="2048 48 3 0.3"

# DeepSeek R1 Optimal (VERIFIED: 5.0 t/s @ 4GB)
# From DSBench.pdf: 11.7 t/s prompt, 5.0 t/s generation
PRESETS[deepseek_r1_fast]="4096 32 4 0.3"

# DeepSeek R1 Quality (4.2 t/s but 8192 context)
PRESETS[deepseek_r1_quality]="8192 16 3 0.3"

# DeepSeek Coder (5-7 t/s measured)
PRESETS[deepseek_coder]="4096 32 4 0.3"

# Extreme Stability (low RAM, guaranteed safe)
PRESETS[stable]="512 32 2 0.2"

# Pythia 70M Speed King (122 t/s measured!)
PRESETS[pythia_70m]="256 256 4 0.9"

apply_preset() {
  local preset_name="$1"
  if [[ -n "${PRESETS[$preset_name]}" ]]; then
    read -r LORNA_CTX LORNA_BATCH LORNA_THREADS LORNA_TEMP <<< "${PRESETS[$preset_name]}"
    export LORNA_CTX LORNA_BATCH LORNA_THREADS LORNA_TEMP
    return 0
  fi
  return 1
}

list_presets() {
  echo -e "${CYAN}${BOLD}Verified Presets (DSBench.pdf measurements):${NC}"
  echo ""
  printf "  ${GOLD}%-22s${NC} ${DIM}%-35s${NC} %s\n" "NAME" "CONFIG" "NOTES"
  echo -e "  ${DIM}──────────────────────────────────────────────────────────────────────${NC}"
  printf "  ${GOLD}%-22s${NC} ${DIM}%-35s${NC} %s\n" \
    "ultrafast" "512ctx/256b/4t/0.7temp" "≤200MB models" \
    "speed" "768ctx/128b/4t/0.6temp" "SmolLM/Qwen 0.5B (13-18 t/s)" \
    "balanced" "1024ctx/64b/4t/0.5temp" "Llama 1B (8-12 t/s)" \
    "quality" "2048ctx/48b/3t/0.3temp" "Reasoning models" \
    "deepseek_r1_fast" "4096ctx/32b/4t/0.3temp" "⭐ R1 5.0 t/s VERIFIED" \
    "deepseek_r1_quality" "8192ctx/16b/3t/0.3temp" "R1 4.2 t/s, max context" \
    "deepseek_coder" "4096ctx/32b/4t/0.3temp" "Coder 5-7 t/s" \
    "stable" "512ctx/32b/2t/0.2temp" "Low RAM guaranteed" \
    "pythia_70m" "256ctx/256b/4t/0.9temp" "🚀 122 t/s speed king"
  echo ""
  echo -e "  ${DIM}Use: lorna solo --preset <name>${NC}"
  echo ""
}
