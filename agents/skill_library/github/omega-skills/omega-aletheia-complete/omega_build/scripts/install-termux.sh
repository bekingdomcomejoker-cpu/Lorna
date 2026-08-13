#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

SOURCE_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
BASE="${CAT_EOF_HOME:-$HOME/cat_eof}"
APP="$BASE/apps/omega-aletheia-claude-bridge"
TOOLS="$BASE/tools"
SECRETS="$BASE/secrets"
STATE="$BASE/state"

mkdir -p "$APP" "$TOOLS" "$SECRETS" "$STATE"

cp -r "$SOURCE_DIR/backend" "$APP/"
cp -r "$SOURCE_DIR/frontend_patch" "$APP/"
cp -r "$SOURCE_DIR/tests" "$APP/"
cp "$SOURCE_DIR/CLAUDE_HANDOFF.md" "$APP/"
cp "$SOURCE_DIR/README.md" "$APP/"
cp "$SOURCE_DIR/anthropic.env.example" "$APP/"

cat > "$TOOLS/omega-claude-bridge" <<'WRAPPER'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

BASE="${CAT_EOF_HOME:-$HOME/cat_eof}"
APP="$BASE/apps/omega-aletheia-claude-bridge"
PID_FILE="$BASE/state/omega-claude-bridge.pid"
LOG_FILE="$BASE/state/omega-claude-bridge.log"
ENV_FILE="$BASE/secrets/anthropic.env"

load_env() {
  if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
  fi
}

case "${1:-status}" in
  start)
    load_env
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "Already running: PID $(cat "$PID_FILE")"
      exit 0
    fi
    nohup python3 "$APP/backend/server.py" >>"$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 1
    echo "Started PID $(cat "$PID_FILE")"
    echo "Log: $LOG_FILE"
    ;;
  foreground)
    load_env
    exec python3 "$APP/backend/server.py"
    ;;
  stop)
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      kill "$(cat "$PID_FILE")"
      rm -f "$PID_FILE"
      echo "Stopped"
    else
      rm -f "$PID_FILE"
      echo "Not running"
    fi
    ;;
  status)
    python3 - <<'PY'
import json, urllib.request
try:
    with urllib.request.urlopen("http://127.0.0.1:8765/api/status", timeout=3) as r:
        print(json.dumps(json.load(r), indent=2))
except Exception as exc:
    print(f"OFFLINE: {exc}")
PY
    ;;
  log)
    tail -n 100 "$LOG_FILE"
    ;;
  *)
    echo "Usage: omega-claude-bridge {start|foreground|stop|status|log}"
    exit 2
    ;;
esac
WRAPPER

chmod +x "$TOOLS/omega-claude-bridge"

if [[ ! -f "$SECRETS/anthropic.env" ]]; then
  cp "$SOURCE_DIR/anthropic.env.example" "$SECRETS/anthropic.env.example"
fi

python3 "$APP/tests/smoke_test.py"

echo
echo "OMEGA · ALETHEIA CLAUDE BRIDGE INSTALLED"
echo "Command: $TOOLS/omega-claude-bridge"
echo "Handoff: $APP/CLAUDE_HANDOFF.md"
echo
echo "Next:"
echo "  cp $SECRETS/anthropic.env.example $SECRETS/anthropic.env"
echo "  chmod 600 $SECRETS/anthropic.env"
echo "  edit the key securely"
echo "  $TOOLS/omega-claude-bridge start"
