#!/usr/bin/env bash
set -euo pipefail
BASE="${CAT_EOF_HOME:-$HOME/cat_eof}"
exec "$BASE/tools/aletheia-console" demo
