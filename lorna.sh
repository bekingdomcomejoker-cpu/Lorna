#!/bin/bash
# LORNA v3 Enterprise — lorna.sh
# Production-grade LLM orchestration with DSBench verified configs

LORNA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$LORNA_DIR/lib/core.sh"
source "$LORNA_DIR/lib/memory.sh"
source "$LORNA_DIR/lib/registry.sh"
source "$LORNA_DIR/lib/presets.sh" 2>/dev/null || true
source "$LORNA_DIR/lib/persist.sh" 2>/dev/null || true

LORNA2_AGENT="$LORNA_DIR/agents/lorna_v2.py"

if [[ -z "$LLAMA_BIN" || ! -x "$LLAMA_BIN" ]]; then
  case "${1:-menu}" in
    agent2|agent|lorna2)
      # Agent mode uses local Ollama rather than llama-cli.
      ;;
    *)
      echo ""
      echo -e "${RED}  ✗ llama-cli binary not found.${NC}"
      echo "  Run: bash $LORNA_DIR/install.sh"
      exit 1
      ;;
  esac
fi

run_lorna2_agent() {
  if [[ ! -f "$LORNA2_AGENT" ]]; then
    err "Lorna2 agent source not found: $LORNA2_AGENT"
    return 1
  fi

  if ! command -v python3 >/dev/null 2>&1; then
    err "python3 is required for Lorna2 Agent"
    return 1
  fi

  if ! python3 -c 'import ollama' >/dev/null 2>&1; then
    err "Python package 'ollama' is required. Install: pip install -r agents/requirements.txt"
    return 1
  fi

  clear
  info "Starting Lorna2 Agent (local interactive mode)"
  python3 "$LORNA2_AGENT"
}

show_menu() {
  lorna_banner

  local free_ram swap_used
  free_ram=$(get_free_ram_mb)
  swap_used=$(get_swap_used_mb)
  local ram_color=$GREEN
  (( free_ram < 600 )) && ram_color=$YELLOW
  (( free_ram < 300 )) && ram_color=$RED

  echo -e "  ${ram_color}RAM: ${free_ram}MB${NC} · ${DIM}Swap: ${swap_used}MB · DSBench Verified${NC}"
  echo ""
  echo -e "  ${GOLD}${BOLD}PIPELINES${NC}"
  echo -e "  ${DIM}────────────────────────────────────────────${NC}"
  echo -e "  ${GOLD}1${NC}   solo         — Single model interactive"
  echo -e "  ${GOLD}2${NC}   chain 2      — 2-model pipeline"
  echo -e "  ${GOLD}3${NC}   chain 3      — Reflex→Think→Code"
  echo -e "  ${GOLD}4${NC}   chain 10     — All top-10 sequential"
  echo -e "  ${GOLD}5${NC}   race 3       — 3 models parallel"
  echo -e "  ${GOLD}6${NC}   cascade      — Historical R→O→W"
  echo ""
  echo -e "  ${CYAN}${BOLD}ENTERPRISE LAB${NC}"
  echo -e "  ${DIM}────────────────────────────────────────────${NC}"
  echo -e "  ${CYAN}7${NC}   ${BOLD}lab${NC}          — Full benchmark lab (exhaustive)"
  echo -e "  ${CYAN}8${NC}   tune quick   — Quick param sweep (36 tests)"
  echo -e "  ${CYAN}9${NC}   tune full    — Full sweep (320 tests)"
  echo -e "  ${CYAN}10${NC}  preset       — List/apply verified presets"
  echo ""
  echo -e "  ${BOLD}TOOLS${NC}"
  echo -e "  ${DIM}────────────────────────────────────────────${NC}"
  echo -e "  ${BOLD}11${NC}  bench        — Benchmark models"
  echo -e "  ${BOLD}12${NC}  health       — System diagnostics"
  echo -e "  ${BOLD}13${NC}  top10        — Speed reference"
  echo -e "  ${BOLD}14${NC}  distill      — LLM Tokenizer & Distillation"
  echo -e "  ${BOLD}15${NC}  agent2       — Lorna2 Agent (chat + local tools)"
  echo ""
  echo -e "  ${DIM}q/quit or /exit — exit  |  Direct: lab, tune quick, preset deepseek_r1_fast, agent2${NC}"
  echo ""
}

route() {
  local cmd="${1:-menu}" arg="${2:-}"

  case "$cmd" in
    solo)
      bash "$LORNA_DIR/pipelines/solo.sh" "$arg"
      ;;
    chain)
      local n="${arg:-2}"
      if ! [[ "$n" =~ ^[0-9]+$ ]] || (( n < 1 || n > 10 )); then
        err "Chain requires 1–10"
        return 1
      fi
      bash "$LORNA_DIR/pipelines/chain.sh" "$n"
      ;;
    race)
      local n="${arg:-3}"
      if ! [[ "$n" =~ ^[0-9]+$ ]] || (( n < 1 || n > 5 )); then
        err "Race requires 1–5"
        return 1
      fi
      bash "$LORNA_DIR/pipelines/race.sh" "$n"
      ;;
    cascade|fusion|warfare)
      bash "$LORNA_DIR/pipelines/cascade.sh"
      ;;
    lab)
      bash "$LORNA_DIR/tools/lab.sh"
      ;;
    tune)
      bash "$LORNA_DIR/tools/tune.sh" "${arg:-quick}"
      ;;
    preset|presets)
      if [[ "$arg" == "list" || -z "$arg" ]]; then
        list_presets
      else
        if apply_preset "$arg"; then
          ok "Preset '$arg' applied for this session"
          info "Example: lorna solo --preset $arg"
        else
          err "Unknown preset: $arg"
          list_presets
        fi
      fi
      ;;
    bench|benchmark)
      bash "$LORNA_DIR/tools/bench.sh" "${arg:-safe}"
      ;;
    health|diag)
      bash "$LORNA_DIR/tools/health.sh"
      ;;
    top10|speeds|table)
      lorna_banner
      print_speed_table
      ;;
    distill|tokenize)
      bash "$LORNA_DIR/tools/distill.sh"
      ;;
    agent2|agent|lorna2)
      run_lorna2_agent
      ;;
    help|--help|-h)
      lorna_banner
      cat << HELP
${BOLD}LORNA v3 Enterprise — DSBench Verified${NC}

${GOLD}Pipelines:${NC}
  lorna solo              → interactive single model
  lorna chain [1-10]      → N-model output chain
  lorna race [1-5]        → parallel tiny model race
  lorna cascade           → Reflex→Oracle→Warfare

${CYAN}Enterprise Lab (NEW):${NC}
  lorna lab               → exhaustive benchmark lab
  lorna tune quick        → quick parameter sweep (36 tests)
  lorna tune full         → full sweep (320 tests)
  lorna preset list       → show verified presets
  lorna preset deepseek_r1_fast  → apply 5.0 t/s config

${BOLD}Tools:${NC}
  lorna bench [mode]      → benchmark models
  lorna health            → full diagnostics
  lorna top10             → speed reference
  lorna agent2            → Lorna2 Agent (chat + local tools)

${BOLD}Verified Configs (DSBench.pdf):${NC}
  DeepSeek R1:  5.0 t/s @ 4096ctx/32b/4t/0.3temp
  Llama 1B:     6.8 t/s @ 1024ctx/64b/4t/0.5temp
  Qwen 0.5B:   15.0 t/s @ 768ctx/128b/4t/0.6temp
  Pythia 70M: 122.0 t/s @ 256ctx/256b/4t/0.9temp

See README_V3_ENTERPRISE.md for full documentation.
HELP
      ;;
    menu|"")
      while true; do
        show_menu
        read -rp "  Select [1-15 or command]: " input
        echo ""

        local parsed_cmd parsed_arg
        read -r parsed_cmd parsed_arg <<< "$input"

        case "$parsed_cmd" in
          1)  route solo ;;
          2)  route chain 2 ;;
          3)  route chain 3 ;;
          4)  route chain 10 ;;
          5)  route race 3 ;;
          6)  route cascade ;;
          7)  route lab ;;
          8)  route tune quick ;;
          9)  route tune full ;;
          10) route preset list ;;
          11) route bench safe ;;
          12) route health ;;
          13) route top10 ;;
          14) route distill ;;
          15) route agent2 ;;
          q|quit|exit|/quit|/exit|"")
            echo ""
            ok "Goodbye."
            echo ""
            exit 0
            ;;
          *)
            if [[ -n "$parsed_cmd" ]]; then
              route "$parsed_cmd" "$parsed_arg"
            fi
            ;;
        esac

        echo ""
        echo -e "${DIM}  ──────────────────────────────────────────${NC}"
        # A route may be followed immediately by /exit in scripted or
        # interactive use; do not require a separate menu cycle to quit.
        read -rp "  Press Enter to return to menu (/exit to quit)... " back
        case "${back,,}" in
          q|quit|exit|/quit|/exit)
            echo ""
            ok "Goodbye."
            echo ""
            exit 0
            ;;
        esac
      done
      ;;
    *)
      err "Unknown command: $cmd"
      route help
      exit 1
      ;;
  esac
}

route "$@"
