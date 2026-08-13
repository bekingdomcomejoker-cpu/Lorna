#!/usr/bin/env bash
set -euo pipefail

PACKAGE_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
BASE="${CAT_EOF_HOME:-$HOME/cat_eof}"

printf '\n%s\n' 'ALETHEIA PERCEPTION INTEGRITY CONSOLE — TERMUX INSTALLER'
printf '%s\n' '========================================================'
printf 'Install target: %s\n\n' "$BASE"

if ! command -v python3 >/dev/null 2>&1; then
  if command -v pkg >/dev/null 2>&1; then
    echo 'Python is missing. Installing it through Termux pkg...'
    pkg install -y python
  else
    echo 'ERROR: python3 is required and pkg is unavailable.' >&2
    exit 2
  fi
fi

mkdir -p \
  "$BASE/tools" \
  "$BASE/registry" \
  "$BASE/schema" \
  "$BASE/input" \
  "$BASE/output/perception_integrity" \
  "$BASE/state" \
  "$BASE/templates" \
  "$BASE/examples/perception_integrity" \
  "$BASE/tests" \
  "$BASE/backups"

BACKUP="$BASE/backups/perception_integrity_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP"

install_preserving() {
  local mode="$1"
  local source="$2"
  local target="$3"
  local package_copy="${target}.perception-package"

  if [[ ! -e "$target" ]]; then
    install -m "$mode" "$source" "$target"
    printf 'Installed: %s\n' "$target"
  elif cmp -s "$source" "$target"; then
    printf 'Already current: %s\n' "$target"
  else
    cp -a "$target" "$BACKUP/"
    install -m "$mode" "$source" "$package_copy"
    printf 'Preserved existing: %s\n' "$target"
    printf 'Packaged version:   %s\n' "$package_copy"
  fi
}

install -m 755 "$PACKAGE_DIR/src/aletheia_console.py" "$BASE/tools/aletheia_console.py"
install -m 755 "$PACKAGE_DIR/bin/aletheia-console" "$BASE/tools/aletheia-console"

install_preserving 644 "$PACKAGE_DIR/data/voice_registry.json" "$BASE/registry/voice_registry.json"
install_preserving 644 "$PACKAGE_DIR/schema/perception_integrity.schema.json" "$BASE/schema/perception_integrity.schema.json"
install_preserving 644 "$PACKAGE_DIR/data/repos-canonical.txt" "$BASE/input/repos-canonical.txt"

install -m 644 \
  "$PACKAGE_DIR/examples/repos-canonical-demo.txt" \
  "$BASE/examples/perception_integrity/repos-canonical-demo.txt"

install -m 644 \
  "$PACKAGE_DIR/examples/repos-observed-demo.txt" \
  "$BASE/examples/perception_integrity/repos-observed-demo.txt"

install -m 755 \
  "$PACKAGE_DIR/tests/test_console.py" \
  "$BASE/tests/test_perception_integrity_console.py"

python3 "$BASE/tests/test_perception_integrity_console.py" "$BASE"

printf '\n%s\n' '======================================================'
printf '%s\n' 'ALETHEIA PERCEPTION INTEGRITY CONSOLE INSTALLED'
printf '%s\n' '======================================================'
printf 'Command: %s\n' "$BASE/tools/aletheia-console"
printf 'Ledger:  %s\n' "$BASE/state/cat_eof.db"
printf 'JSONL:   %s\n' "$BASE/state/perception_integrity.jsonl"
printf '\nUseful commands:\n'
printf '  %s\n' "$BASE/tools/aletheia-console status"
printf '  %s\n' "$BASE/tools/aletheia-console demo"
printf '  %s\n' "$BASE/tools/aletheia-console wizard"
printf '  %s\n' "$BASE/tools/aletheia-console voice 'Manuscriptly'"
