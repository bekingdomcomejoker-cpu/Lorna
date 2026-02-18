#!/bin/bash
# ============================================================
# LORNA — install.sh  (v2)
# One-shot setup for Termux on Redmi 13C or any 4GB Android
# ============================================================

set -e

RED='\033[0;31m' GREEN='\033[0;32m' CYAN='\033[0;36m'
YELLOW='\033[1;33m' BOLD='\033[1m' DIM='\033[2m' NC='\033[0m'
ok()   { echo -e "${GREEN}  ✓${NC} $*"; }
info() { echo -e "${CYAN}  ·${NC} $*"; }
warn() { echo -e "${YELLOW}  ⚠${NC} $*"; }
err()  { echo -e "${RED}  ✗${NC} $*"; }

clear
echo -e "${CYAN}${BOLD}"
echo "  ██╗      ██████╗ ██████╗ ███╗   ██╗ █████╗ "
echo "  ██║     ██╔═══██╗██╔══██╗████╗  ██║██╔══██╗"
echo "  ██║     ██║   ██║██████╔╝██╔██╗ ██║███████║"
echo "  ██║     ██║   ██║██╔══██╗██║╚██╗██║██╔══██║"
echo "  ███████╗╚██████╔╝██║  ██║██║ ╚████║██║  ██║"
echo "  ╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝"
echo -e "${NC}${DIM}  Installing LORNA v2...${NC}"
echo ""

LORNA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ─── 1. Permissions ─────────────────────────────────────────
info "Setting script permissions..."
find "$LORNA_DIR" -name "*.sh" -exec chmod +x {} \;
ok "All scripts executable"

# ─── 2. Detect llama.cpp ────────────────────────────────────
info "Checking for llama-cli binary..."
LLAMA_MAIN="/data/data/com.termux/files/home/llama.cpp/build/bin/llama-cli"

if [[ -x "$LLAMA_MAIN" ]]; then
  size=$(stat -c%s "$LLAMA_MAIN" 2>/dev/null || echo 0)
  if (( size >= 10000000 )); then
    ok "Found good build: $LLAMA_MAIN (${size} bytes)"
  else
    warn "Found binary at $LLAMA_MAIN but it's only ${size} bytes — may be old build"
    warn "Consider rebuilding (see instructions below)"
  fi
else
  warn "llama.cpp not found at expected path: $LLAMA_MAIN"
  echo ""
  echo -e "  ${BOLD}Build from source:${NC}"
  echo "    pkg install cmake git clang -y"
  echo "    git clone https://github.com/ggerganov/llama.cpp ~/llama.cpp"
  echo "    cd ~/llama.cpp"
  echo "    cmake -B build -DLLAMA_BUILD_SERVER=OFF -DLLAMA_BUILD_TESTS=OFF"
  echo "    cmake --build build --config Release -j4"
  echo ""
  read -rp "  Build now? [y/N]: " do_build
  if [[ "${do_build,,}" == "y" ]]; then
    pkg install cmake git clang -y
    [[ ! -d ~/llama.cpp ]] && git clone https://github.com/ggerganov/llama.cpp ~/llama.cpp
    cd ~/llama.cpp
    cmake -B build -DLLAMA_BUILD_SERVER=OFF -DLLAMA_BUILD_TESTS=OFF
    cmake --build build --config Release -j4
    ok "Build complete"
  fi
fi

# ─── 3. Fix PATH ────────────────────────────────────────────
info "Checking PATH configuration..."
BASHRC="$HOME/.bashrc"
MARKER="# LORNA PATH CONFIG"

if ! grep -q "$MARKER" "$BASHRC" 2>/dev/null; then
  cat >> "$BASHRC" << 'BASHRC_BLOCK'

# LORNA PATH CONFIG — added by install.sh
# Puts the correct (large, full-build) llama-cli binary at front of PATH
# to override any federation symlinks
export PATH="/data/data/com.termux/files/usr/bin:$HOME/llama.cpp/build/bin:$HOME/.local/bin:$PATH"
alias lorna='bash /data/data/com.termux/files/home/lorna-mobile-llm-fixed/lorna.sh'
BASHRC_BLOCK
  ok "PATH fixed in ~/.bashrc"
  ok "Alias 'lorna' added"
else
  ok "PATH already configured"
fi

# ─── 4. Directories ─────────────────────────────────────────
mkdir -p "$HOME/lorna_logs"
LORNA_TMP="${TMPDIR:-/data/data/com.termux/files/usr/tmp}/lorna"
mkdir -p "$LORNA_TMP/chain" "$LORNA_TMP/race" "$LORNA_TMP/cascade" "$LORNA_TMP/bench"
ok "Directories created"

# ─── 5. Model scan ──────────────────────────────────────────
info "Scanning for existing GGUF models..."
model_count=$(find ~ -type f -name "*.gguf" ! -name "ggml-vocab-*" -size +50M 2>/dev/null | wc -l)
ok "Found ${model_count} model file(s)"

if (( model_count == 0 )); then
  echo ""
  warn "No models found. Download examples:"
  echo ""
  echo "  # Qwen 0.5B — fastest daily driver:"
  echo "  mkdir -p ~/federation/models && cd ~/federation/models"
  echo "  wget https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
  echo ""
  echo "  # Llama 1B — best quality/speed balance:"
  echo "  wget https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"
fi

# ─── 6. Quick smoke test ────────────────────────────────────
echo ""
info "Testing binary..."
source "$LORNA_DIR/lib/core.sh" 2>/dev/null || true
if [[ -n "$LLAMA_BIN" && -x "$LLAMA_BIN" ]]; then
  sz=$(stat -c%s "$LLAMA_BIN" 2>/dev/null || echo 0)
  ok "LORNA will use: $LLAMA_BIN (${sz} bytes)"
else
  warn "Binary still not found — run install again after building llama.cpp"
fi

# ─── Done ───────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}  ═══════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  ✓ LORNA installed${NC}"
echo -e "${GREEN}${BOLD}  ═══════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}Next steps:${NC}"
echo "  1.  source ~/.bashrc"
echo "  2.  lorna"
echo "  or: bash $LORNA_DIR/lorna.sh"
echo ""
