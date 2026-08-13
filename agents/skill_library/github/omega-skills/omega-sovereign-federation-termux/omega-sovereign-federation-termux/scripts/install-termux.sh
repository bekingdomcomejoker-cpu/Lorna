#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

SOURCE="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
BASE="${CAT_EOF_HOME:-$HOME/cat_eof}"
APP="$BASE/apps/omega-sovereign-federation"
TOOLS="$BASE/tools"
SECRETS="$BASE/secrets"
BACKUPS="$BASE/backups/omega-sovereign-federation"

echo "OMEGA SOVEREIGN FEDERATION — TERMUX INSTALLER"
echo "=============================================="
echo "Target: $APP"

mkdir -p "$BASE" "$TOOLS" "$SECRETS" "$BACKUPS" "$BASE/state" "$BASE/registry"

if [[ -d "$APP" ]]; then
  stamp="$(date +%Y%m%d_%H%M%S)"
  cp -a "$APP" "$BACKUPS/$stamp"
  echo "Backed up prior federation app: $BACKUPS/$stamp"
fi

rm -rf "$APP"
mkdir -p "$APP"
cp -a "$SOURCE"/. "$APP"/

cat > "$TOOLS/omega-federation" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
BASE="${CAT_EOF_HOME:-$HOME/cat_eof}"
APP="$BASE/apps/omega-sovereign-federation"
ENV="$BASE/secrets/federation.env"
if [[ -f "$ENV" ]]; then
  # shellcheck disable=SC1090
  source "$ENV"
fi
export PYTHONPATH="$APP${PYTHONPATH:+:$PYTHONPATH}"
exec python3 "$APP/federation/cli.py" "$@"
EOF
chmod +x "$TOOLS/omega-federation"

if [[ ! -f "$SECRETS/federation.env.example" ]]; then
  cp "$SOURCE/config/federation.env.example" "$SECRETS/federation.env.example"
fi

if [[ ! -f "$BASE/registry/voice_registry.json" ]]; then
  cp "$SOURCE/examples/voice_registry.json" "$BASE/registry/voice_registry.json"
  echo "Installed initial voice registry"
else
  cp "$SOURCE/examples/voice_registry.json" "$BASE/registry/voice_registry.json.federation-package"
  echo "Preserved existing voice registry"
fi

export PYTHONPATH="$APP${PYTHONPATH:+:$PYTHONPATH}"
python3 -m unittest discover -s "$APP/tests" -v

echo
echo "OMEGA SOVEREIGN FEDERATION INSTALLED"
echo "Command: $TOOLS/omega-federation"
echo
echo "Start:"
echo "  $TOOLS/omega-federation serve start"
echo
echo "Open:"
echo "  http://127.0.0.1:8765"
echo
echo "Configure optional providers:"
echo "  $TOOLS/omega-federation configure"
