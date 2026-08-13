#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
HERE="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
export PYTHONPATH="$HERE${PYTHONPATH:+:$PYTHONPATH}"
python3 -m unittest discover -s "$HERE/tests" -v
