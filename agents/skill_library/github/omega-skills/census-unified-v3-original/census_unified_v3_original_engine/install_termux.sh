#!/data/data/com.termux/files/usr/bin/bash
set -e

termux-setup-storage || true
pkg install -y python unzip sqlite

ROOT="$HOME/omega_apps/census_unified_v3/census_unified_v3_original_engine"
mkdir -p "$HOME/.omega/census"
mkdir -p "$HOME/.omega/sources"
mkdir -p "$HOME/bin"

chmod +x "$ROOT/history_extractor.py" "$ROOT/omega_guardian_engine.py" "$ROOT/review_canon.py" "$ROOT/census_engine/cli.py"

cat > "$HOME/bin/census" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
cd "$ROOT"
python -m census_engine.cli "\$@"
EOF
chmod +x "$HOME/bin/census"

echo
echo "[✓] Census Unified v3 installed."
echo "Add this to PATH if needed:"
echo 'export PATH="$HOME/bin:$PATH"'
echo
echo "Run:"
echo "  census init"
echo "  census extract --input ~/storage/downloads/chatgpt_export --out ~/.omega/census/history_events.jsonl"
echo "  census guardian --input ~/storage/downloads/source_files --out ~/.omega/census/guardian_events.jsonl"
echo "  census review --limit 25"
echo "  census report --out ~/.omega/census/CENSUS_REPORT.md"
