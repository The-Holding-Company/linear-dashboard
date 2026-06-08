#!/usr/bin/env bash
# Refresh the Linear dashboard (fetches issues + renders HTML).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
python3 "$HERE/src/build.py" "$@"
echo "open $HERE/dist/index.html"
